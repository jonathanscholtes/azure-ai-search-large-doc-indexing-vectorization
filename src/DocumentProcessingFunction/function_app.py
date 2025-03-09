import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SemanticConfiguration,
    SemanticField,
    VectorSearch,
    VectorSearchProfile,
    SemanticPrioritizedFields,
    HnswAlgorithmConfiguration,
    SemanticSearch
)
from azure.core.exceptions import ResourceNotFoundError
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging
import traceback
from os import environ
import io
import fitz
import uuid
from typing import List


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.blob_trigger(arg_name="myblob", path="load", connection="BlobTriggerConnection")
def Loaders(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob\n"
                    f"Name: {myblob.name}\n"
                    f"Blob Size: {myblob.length} bytes")
    


     # Validate the file extension
    if not myblob.name.lower().endswith('.pdf'):
        return f"Skipping processing: {myblob.name} is not a .pdf file."

    try:
        credential = DefaultAzureCredential()

        # Set the API type to `azure_ad`
        environ["OPENAI_API_TYPE"] = "azure_ad"
        # Set the API_KEY to the token from the Azure credential
        token = credential.get_token("https://cognitiveservices.azure.com/.default").token
        environ["OPENAI_API_KEY"] = token

        environ["AZURE_OPENAI_AD_TOKEN"] = environ["OPENAI_API_KEY"]

        AZURE_STORAGE_URL = environ.get("BlobTriggerConnection__blobServiceUri")

        logging.info(f"Create embeddings")
        embeddings: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings(
        azure_deployment=environ.get("AZURE_OPENAI_EMBEDDING"),
        openai_api_version=environ.get("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=environ.get("AZURE_OPENAI_ENDPOINT"),
        api_key=environ.get("AZURE_OPENAI_API_KEY"),)

        logging.info(f"****** Processing PDF Document *****")

        blob_content = myblob.read()
        pdf_file = io.BytesIO(blob_content)

        logging.info(f"****** Chunking Document *****")

        file_name = myblob.name.split('/')[-1] 
        loader = DocumentLoader(pdf_file)
        chunks = loader.load_chunk_document(title=file_name, chunk_size=int(environ.get("DOCUMENT_CHUNK_SIZE")),chunk_overlap=int(environ.get("DOCUMENT_CHUNK_OVERLAP")))
        

        logging.info(f"****** Loading Index *****")

        AISearchIndexLoader(embeddings,credential,logging,int(environ.get("AZURE_AI_SEARCH_BATCH_SIZE"))).populate_search_index(chunks)


        blobManager = BlobManager()
        
        container, blob_name = blobManager.move_blob(myblob,blob_content)
        blobManager.delete_blob(container, blob_name)

    except Exception as e:
        logging.error(f"loader Failed: {e}")
        logging.error(traceback.format_exc())


class DocumentLoader:
    def __init__(self, stream):
        self.stream = stream

    def _create_document(self,page:fitz.Page, index:int, title:str):
        document = Document(
        page_content=page.get_text(),
        metadata={"title": title, "page_number":index+1}
        )

        return document
        

    def load_chunk_document(self, title,
                            chunk_size=2000, 
                    chunk_overlap=500,
                    length_function=len,
                    is_separator_regex=False) -> List[Document]:
        
        logging.info(f"Load and return documents from the PDF bytes.")
        
        documents: List[Document] = []
        
        doc = fitz.open(stream=self.stream)

        documents: list[Document] = [self._create_document(page, index, title) for index, page in enumerate(doc)]
    
        text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap,
        length_function=length_function,
        is_separator_regex=is_separator_regex
        )

        chunks = text_splitter.split_documents(documents)

        for chunk in chunks:
            chunk.metadata["chunk_id"] = str(uuid.uuid4()) 

        return chunks



class AISearchIndexLoader:
    def __init__(self, embeddings, credential,logging, batch_size):
        self.logger = logging
        self.embeddings = embeddings
        self.batch_size = batch_size
       
         # Configuration for Azure Cognitive Search
        search_endpoint = environ["AZURE_AI_SEARCH_ENDPOINT"]
        self.index_name = environ["AZURE_AI_SEARCH_INDEX"]

        # Create SearchClient
        self.search_client = SearchClient(endpoint=search_endpoint, index_name=self.index_name, credential=credential)

        # Create SearchIndexClient
        self.search_index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    
    def populate_search_index(self,chunks:List[Document]):
        index_exists = False

        # Check if the index exists and contains documents
        try:
            self.logger.info("Verifying if AI Search index exists...")
            index_response = self.search_index_client.get_index(self.index_name)
            index_exists = True

        except ResourceNotFoundError:
            self.logger.info("AI Search index not found, creating index...")

        # Create the index if it doesn't exist
        if not index_exists:

            semantic_config =SemanticConfiguration(
                           name="default",
                            prioritized_fields=SemanticPrioritizedFields(
                               title_field=SemanticField(field_name="title"),
                               content_fields=[SemanticField(field_name="content")]
                           ))

            index = SearchIndex(
                name=self.index_name,
                fields=[
                    SimpleField(name="chunk_id", type="Edm.String", key=True, filterable=True, sortable=True),
                    SearchableField(name="content", type="Edm.String", filterable=True, sortable=True),
                    SearchableField(name="title", type="Edm.String", filterable=True, sortable=True),
                    SearchableField(name="pageNumber", type="Edm.Int", filterable=True, sortable=True),
                    SearchField(name="content_vector", type="Collection(Edm.Single)", vector_search_dimensions=1536, vector_search_profile_name="my-vector-config")
                ],
                
                semantic_search= SemanticSearch(configurations=[semantic_config]),
               
                vector_search = VectorSearch(
                        profiles=[VectorSearchProfile(name="my-vector-config", algorithm_configuration_name="my-algorithms-config")],
                        algorithms=[HnswAlgorithmConfiguration(name="my-algorithms-config", kind="hnsw")],
                    )

            )

            try:
                self.search_index_client.create_index(index)
            except Exception as ex:
                self.logger.info("Index was created on different thread")

       
        try:
            
            documents = []
            batch_size = self.batch_size 
            total_batches = (len(chunks) + batch_size - 1) // batch_size  
            batches_processed = 0  

            for index, chunk in enumerate(chunks):
                try:
                    # Extract chunk metadata
                    chunk_id = str(chunk.metadata["chunk_id"])
                    content = str(chunk.page_content)
                    title = str(chunk.metadata["title"])
                    page_number = str(chunk.metadata["page_number"]) 
                    
                    # Generate the embedding for the content
                    embedding = self.embeddings.embed_query(content)

                    # Add the document to the batch
                    documents.append({
                        "chunk_id": chunk_id,
                        "content": content,
                        "title": title,
                        "pageNumber": page_number,
                        "content_vector": embedding
                    })

                    
                    if (index + 1) % batch_size == 0 or (index + 1) == len(chunks):  
                        result = self.search_client.upload_documents(documents=documents)

                        #self.logger.info(f"Upload of batch of {len(documents)} documents succeeded: {result[0].succeeded}")

                        batches_processed += 1
                        batches_remaining = total_batches - batches_processed
                        self.logger.info(f"Batch {batches_processed}/{total_batches} uploaded. Remaining: {batches_remaining}")

                        
                        # Clear the documents list for the next batch
                        documents = []
                except Exception as ex:
                    self.logger.info((chunk))
                    raise ex

        except Exception as ex:
            self.logger.error("Error in AI Search: %s", ex)
            raise ex


class BlobManager():

    def __init__(self):
        credential = DefaultAzureCredential()
        AZURE_STORAGE_URL = environ.get("AZURE_STORAGE_URL")
        # Create the BlobServiceClient object    
        self.blob_service_client =  BlobServiceClient(AZURE_STORAGE_URL, credential=credential)    


    def load_data(self,data, blob_name:str, container_name:str):     

      
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Upload the blob data - default blob type is BlockBlob
        blob_client.upload_blob(data,overwrite=True)

    def move_blob(self,myblob, blob_content):
        # Delete the blob after processing
   
        container_name, blob_name = "load", myblob.name.split('/')[-1]  # Adjust based on the blob path structure

        blob_client_completed = self.blob_service_client.get_blob_client(container="completed", blob=blob_name)
        blob_client_completed.upload_blob(blob_content,overwrite=True)

        return container_name, blob_name

    def delete_blob(self,container_name,blob_name):
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.delete_blob()
        logging.info(f"Deleted blob: {blob_name}")
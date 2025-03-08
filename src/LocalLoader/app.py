import fitz
from langchain_core.documents import Document
from azure.core.credentials import AzureKeyCredential
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging
import uuid
from typing import List
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
from os import environ
from dotenv import load_dotenv
import argparse


load_dotenv(override=False)


class DocumentLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

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
        
        logging.info(f"Load and return documents from the PDF file.")
        
        documents: List[Document] = []
        
        doc = fitz.open(self.file_path)

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
    def __init__(self, embeddings, credential,logging):
        self.logger = logging
        self.embeddings = embeddings
       
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
            batch_size = 100 
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

                        #print(f"Upload of batch of {len(documents)} documents succeeded: {result[0].succeeded}")

                        batches_processed += 1
                        batches_remaining = total_batches - batches_processed
                        print(f"Batch {batches_processed}/{total_batches} uploaded. Remaining: {batches_remaining}")

                        
                        # Clear the documents list for the next batch
                        documents = []
                except Exception as ex:
                    print(chunk)
                    raise ex

        except Exception as ex:
            self.logger.error("Error in AI Search: %s", ex)
            raise ex




def main(files: list):
    
    #logging.basicConfig(level=logging.INFO)

   
    credential = AzureKeyCredential(environ["AZURE_AI_SEARCH_KEY"])

    # Create embeddings using Azure OpenAI
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=environ.get("AZURE_OPENAI_EMBEDDING"),
        openai_api_version=environ.get("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=environ.get("AZURE_OPENAI_ENDPOINT"),
        api_key=environ.get("AZURE_OPENAI_API_KEY"),
    )


    for file_path in files:
        file_name = file_path.split('\\')[-1] 

        print(f'Load Document: {file_name}')

        # Document loader
        loader = DocumentLoader(file_path)
        chunks = loader.load_chunk_document(title=file_name)

        print("Create embeddings")

        # Populate the search index with chunks
        AISearchIndexLoader(embeddings, credential, logging).populate_search_index(chunks)


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Process PDF files for indexing into Azure AI Search")
    parser.add_argument('--files', type=str, required=True, help="Semicolon separated list of file paths")
    
    args = parser.parse_args()
    
    # Split the files string into a list
    files = args.files.split(";")
    main(files)
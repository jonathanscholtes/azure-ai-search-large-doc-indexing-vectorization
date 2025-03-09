import azure.functions as func
import azure.durable_functions as df
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField,
    VectorSearch, VectorSearchProfile, HnswAlgorithmConfiguration, 
    SemanticConfiguration, SemanticField, SemanticSearch, SemanticPrioritizedFields
)
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
import logging
from os import environ
import io
import fitz
import uuid

myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@myApp.blob_trigger(arg_name="myblob", path="load", connection="BlobTriggerConnection")
@myApp.durable_client_input(client_name="client")
async def blob_trigger_start(myblob: func.InputStream, client):
    logging.info(f"Python blob trigger function processed blob\n"
                    f"Name: {myblob.name}\n"
                    f"Blob Size: {myblob.length} bytes")
    

    # Start the orchestration and pass the input data to the orchestrator function
    instance_id = yield client.start_new("orchestrator_function")

    logging.info(f"Started orchestration with ID = '{instance_id}'.")

    return instance_id 


@myApp.orchestration_trigger(context_name="context")
def orchestrator_function(context: df.DurableOrchestrationContext):
    input_data = context.get_input()
    file_name = input_data['blob_name']

    logging.info(f"Starting orchestration for file: {file_name}")

    # Validate the file extension
    if not file_name.lower().endswith('.pdf'):
        return f"Skipping processing: {file_name} is not a .pdf file."

    # 1. Ensure the AI Search Index exists
    yield context.call_activity("create_search_index")

    # 2. Chunk and process the document
    chunks = yield context.call_activity("chunk_document", input_data)

    # 3. Index the document in Azure AI Search
    yield context.call_activity("index_document", chunks)

    # 4. Move processed blob to 'completed' container
    yield context.call_activity("move_blob", input_data)

    # 5. Delete original blob
    yield context.call_activity("delete_blob", input_data)

    return "Processing Complete"


@myApp.activity_trigger()
def create_search_index():
    credential = DefaultAzureCredential()
    search_client = SearchIndexClient(
        endpoint=environ["AZURE_AI_SEARCH_ENDPOINT"],
        credential=credential
    )

    index_name = environ["AZURE_AI_SEARCH_INDEX"]

    try:
        search_client.get_index(index_name)
        logging.info("Azure AI Search index already exists.")
    except:
        logging.info("Creating Azure AI Search index...")

        semantic_config = SemanticConfiguration(
            name="default",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="title"),
                content_fields=[SemanticField(field_name="content")]
            )
        )

        index = SearchIndex(
            name=index_name,
            fields=[
                SimpleField(name="chunk_id", type="Edm.String", key=True, filterable=True, sortable=True),
                SearchableField(name="content", type="Edm.String", filterable=True, sortable=True),
                SearchableField(name="title", type="Edm.String", filterable=True, sortable=True),
                SearchableField(name="pageNumber", type="Edm.Int32", filterable=True, sortable=True),
                SearchField(name="content_vector", type="Collection(Edm.Single)", 
                            vector_search_dimensions=1536, vector_search_profile_name="my-vector-config")
            ],
            semantic_search=SemanticSearch(configurations=[semantic_config]),
            vector_search=VectorSearch(
                profiles=[VectorSearchProfile(name="my-vector-config", algorithm_configuration_name="my-algorithms-config")],
                algorithms=[HnswAlgorithmConfiguration(name="my-algorithms-config", kind="hnsw")]
            )
        )

        search_client.create_index(index)
        logging.info("Azure AI Search index created.")


@myApp.activity_trigger(input_name="input_data")
def chunk_document(input_data: dict):
    blob_content = input_data["blob_content"]
    file_name = input_data["blob_name"].split('/')[-1]

    pdf_file = io.BytesIO(blob_content)

    logging.info("Chunking Document...")

    # Load PDF
    doc = fitz.open(stream=pdf_file)
    documents = [
        Document(page_content=page.get_text(), metadata={"title": file_name, "page_number": i + 1})
        for i, page in enumerate(doc)
    ]

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=environ.get("DOCUMENT_CHUNK_SIZE"), chunk_overlap=environ.get("DOCUMENT_CHUNK_OVERLAP"))
    chunks = text_splitter.split_documents(documents)

    # Generate Embeddings
    logging.info("Generating embeddings for chunks...")

    credential = DefaultAzureCredential()
    environ["OPENAI_API_KEY"] = credential.get_token("https://cognitiveservices.azure.com/.default").token

    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=environ.get("AZURE_OPENAI_EMBEDDING"),
        openai_api_version=environ.get("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=environ.get("AZURE_OPENAI_ENDPOINT"),
        api_key=environ.get("OPENAI_API_KEY"),
    )

    for chunk in chunks:
        chunk.metadata["chunk_id"] = str(uuid.uuid4())
        chunk.metadata["content_vector"] = embeddings.embed_query(chunk.page_content)  # Generate embeddings

    return chunks


@myApp.activity_trigger(input_name="chunks")
def index_document(chunks):
    logging.info("Indexing document into Azure AI Search...")

    # Initialize credential and search client
    credential = DefaultAzureCredential()
    search_client = SearchClient(
        endpoint=environ["AZURE_AI_SEARCH_ENDPOINT"],
        index_name=environ["AZURE_AI_SEARCH_INDEX"],
        credential=credential
    )

    # Batch size
    batch_size = environ.get("AZURE_AI_SEARCH_BATCH_SIZE")  

    # Split the chunks into smaller batches
    document_batches = [
        chunks[i:i + batch_size]
        for i in range(0, len(chunks), batch_size)
    ]

    # Iterate over each batch
    for batch in document_batches:
        # Prepare the documents to upload
        documents = [
            {
                "chunk_id": chunk.metadata["chunk_id"],
                "content": chunk.page_content,
                "title": chunk.metadata["title"],
                "pageNumber": chunk.metadata["page_number"],
                "content_vector": chunk.metadata["content_vector"]
            }
            for chunk in batch
        ]

        # Upload the batch to Azure AI Search
        result = search_client.upload_documents(documents=documents)

        if result[0].succeeded:
            logging.info(f"Batch of {len(documents)} documents indexed successfully.")
        else:
            logging.error(f"Batch failed to index: {result[0].error_message}")

    logging.info("Document indexing complete.")


@myApp.activity_trigger(input_name="input_data")
def move_blob(input_data: dict):
    blob_name = input_data["blob_name"]
    blob_content = input_data["blob_content"]

    credential = DefaultAzureCredential()
    blob_service_client = BlobServiceClient(account_url=environ["AZURE_STORAGE_URL"], credential=credential)

    destination_container = "completed"
    blob_client = blob_service_client.get_blob_client(container=destination_container, blob=blob_name)
    blob_client.upload_blob(blob_content, overwrite=True)

    logging.info(f"Moved blob to {destination_container}/{blob_name}")


@myApp.activity_trigger(input_name="input_data")
def delete_blob(input_data: dict):
    blob_name = input_data["blob_name"]

    credential = DefaultAzureCredential()
    blob_service_client = BlobServiceClient(account_url=environ["AZURE_STORAGE_URL"], credential=credential)

    container_name = "load"
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    blob_client.delete_blob()
    logging.info(f"Deleted blob: {blob_name} from {container_name}")

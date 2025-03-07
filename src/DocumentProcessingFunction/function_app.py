import azure.functions as func
import azure.durable_functions as df
import logging
import base64
import io
import fitz
from os import environ
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



myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@myApp.blob_trigger(arg_name="myblob", path="load", connection="BlobTriggerConnection")
@myApp.durable_client_input(client_name="client")
async def blob_trigger_start(myblob: func.InputStream, client):
    logging.info(f"Python blob trigger function processed blob\n"
                    f"Name: {myblob.name}\n"
                    f"Blob Size: {myblob.length} bytes")
    
    # Read the blob content
    base64_bytes = base64.b64encode(myblob.read())

    # Start the Durable Functions orchestration
    instance_id = await client.start_new("document_orchestrator", None, {"filename":myblob.name,"data": base64_bytes.decode('ascii')})
    logging.info(f"Started orchestration with ID = '{instance_id}'.")




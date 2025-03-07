from dotenv import load_dotenv
from os import environ
from langchain.globals import set_llm_cache
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_openai import AzureOpenAIEmbeddings

load_dotenv(override=False)

vector_store : AzureSearch | None=None


def search_init():
    global vector_store
    
      # Use AzureOpenAIEmbeddings with an Azure account
    embeddings: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings(
        azure_deployment=environ.get("AZURE_OPENAI_EMBEDDING"),
        openai_api_version=environ.get("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=environ.get("AZURE_OPENAI_ENDPOINT"),
        api_key=environ.get("AZURE_OPENAI_API_KEY"),)
    
    vector_store = AzureSearch(
        azure_search_endpoint=environ.get("AZURE_AI_SEARCH_ENDPOINT"),
        azure_search_key=environ.get("AZURE_AI_SEARCH_KEY"),
        index_name=environ.get("AZURE_AI_SEARCH_INDEX"),
        embedding_function=embeddings.embed_query,
        semantic_configuration_name= 'default'
    )

search_init()
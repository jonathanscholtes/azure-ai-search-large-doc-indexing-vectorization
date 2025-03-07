from dotenv import load_dotenv
from os import environ
from langchain_openai import AzureChatOpenAI


# Load environment variables from .env file
load_dotenv(override=False)

# Initialize the AzureChatOpenAI model
llm: AzureChatOpenAI | None = None

def initialize_llm():
    """Initialize the Azure Chat OpenAI model with specified parameters."""
    global llm


    llm = AzureChatOpenAI(
        temperature=0,
        azure_deployment=environ["AZURE_OPENAI_MODEL"]

    )


initialize_llm()


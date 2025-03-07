from pydantic import BaseModel, Field
from typing import List

class DocumentResource(BaseModel):
    title: str = Field(description="The name of the BoardGame") 
    content: str = Field(description="The boardgamegeek rating") 
    pageNumber: int = Field(description="The numbers of players") 


class DocumentResponse(BaseModel):
    answer: str = Field(description="The answer from the LLM ") 
    Documents: List[DocumentResource] = Field(description="The document returned from Azure AI Search") 
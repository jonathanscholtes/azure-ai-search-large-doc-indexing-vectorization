from pydantic import BaseModel, Field
from typing import List

class DocumentResource(BaseModel):
    title: str = Field(description="The document title") 
    content: str = Field(description="The document text") 
    pageNumber: int = Field(description="The document page number") 


class DocumentResponse(BaseModel):
    answer: str = Field(description="The answer from the LLM ") 
    Documents: List[DocumentResource] = Field(description="The document returned from Azure AI Search") 
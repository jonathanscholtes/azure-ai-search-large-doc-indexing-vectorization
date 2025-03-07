from .init import vector_store
from model.DocumentProcessing import DocumentResource
from langchain.docstore.document import Document
from typing import List

def results_to_model(result:Document) -> DocumentResource:
    return DocumentResource( title = result.metadata["title"],
                        pageNumber=result.metadata["pageNumber"],
                        content=result.page_content)

                       

def hybrid_search(query:str) ->List[DocumentResource]:

    docs = vector_store.semantic_hybrid_search(
    query=query,
    k=3
    )


    return [results_to_model(document) for document in docs]
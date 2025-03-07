
from .init import llm
from data.aisearch import search
from langchain.docstore.document import Document
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from model.DocumentProcessing import DocumentResource, DocumentResponse

# Define a prompt template for the main query processing
template: str = """Use the provided context to answer the question. If the context does not contain the answer, simply state that you don’t know.
                    Your response should be informative and concise, using no more than four sentences.

                    Context: {context}

                    Question: {question}

                    Answer:"""


def get_qa_from_query(query: str) -> DocumentResponse:
    """Perform a Q&A based on the provided query."""
    print('** Q/A From Query **')
    documents = search.hybrid_search(query)

    if not documents:
        return DocumentResponse(text="No Documents Found", Documents=[])

    custom_rag_prompt = PromptTemplate.from_template(template)

    def format_docs(docs):
        """Format document contents for the RAG chain."""
        return "\n\n".join(doc.content for doc in docs)

    content = format_docs(documents)

    rag_chain = (
        {"context": lambda x: content, "question": RunnablePassthrough()}
        | custom_rag_prompt
        | llm
        | StrOutputParser()
    )

    answer = rag_chain.invoke(query)
    return DocumentResponse(answer=answer, Documents=documents)
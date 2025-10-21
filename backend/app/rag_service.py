import os
import json
import re
from pydantic import ValidationError

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from .prompts import get_requirements_generation_prompt
from .schemas import GeneratedRequirements
from .database_ops import save_requirements_to_db

COLLECTION_NAME = "document_chunks"

def get_vector_store():
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
    embeddings = OpenAIEmbeddings()
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = "localhost"
    port = os.getenv("POSTGRES_PORT")
    dbname = os.getenv("POSTGRES_DB")
    connection = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"
    return PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=connection,
        use_jsonb=True,
    )

def process_and_store_document(document):
    print(f"Starting RAG processing for document ID: {document.id}...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.create_documents(
        [document.content],
        metadatas=[{"document_id": str(document.id)}]
    )
    vector_store = get_vector_store()
    vector_store.add_documents(docs)
    print(f"Successfully processed and stored {len(docs)} chunks for document ID: {document.id}")


def clean_llm_output(raw_output: str) -> str:
    """
    Cleans the raw LLM string output by removing markdown code fences
    and extracting only the JSON object.
    """
    match = re.search(r'```(json)?\s*(\{.*?\})\s*```', raw_output, re.DOTALL)
    if match:
        return match.group(2)
    return raw_output.strip()


def analyze_document_and_generate_requirements(user_query: str, document_id: int):
    """
    The main analysis pipeline: RAG, LLM call, cleaning, validation, retry, and saving.
    """
    print(f"Starting analysis for document ID: {document_id} with query: '{user_query}'")
    
    vector_store = get_vector_store()
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    retriever = vector_store.as_retriever(
        search_kwargs={'filter': {'document_id': str(document_id)}}
    )

    error_message = None
    max_retries = 2

    for i in range(max_retries):
        print(f"Analysis attempt {i + 1}...")

        prompt_text = get_requirements_generation_prompt(
            context="{context}",
            user_query="{input}",
            error_message=error_message
        )
        prompt = ChatPromptTemplate.from_template(prompt_text)
        
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        rag_chain = (
            {"context": retriever | format_docs, "input": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        raw_output = rag_chain.invoke(user_query)

        try:
            cleaned_output = clean_llm_output(raw_output)
            validated_data = GeneratedRequirements.model_validate_json(cleaned_output)
            print("LLM output cleaned and validated successfully!")
            
            save_requirements_to_db(validated_data, document_id)
            
            return "Analysis complete. Requirements have been generated and saved."

        except (ValidationError, json.JSONDecodeError) as e:
            print(f"Validation failed on attempt {i + 1}: {e}")
            error_message = str(e)
            if i == max_retries - 1:
                raise Exception("Failed to generate valid JSON after multiple retries.") from e

    raise Exception("An unexpected error occurred in the analysis pipeline.")
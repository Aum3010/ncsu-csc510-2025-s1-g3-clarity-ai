import os
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

COLLECTION_NAME = "document_chunks"

def get_vector_store():
    """Initializes and returns the PGVector vector store based on the latest documentation."""
    embeddings = OpenAIEmbeddings()

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = "localhost"
    port = os.getenv("POSTGRES_PORT")
    dbname = os.getenv("POSTGRES_DB")

    # CORRECTED: Use the 'psycopg' driver for psycopg3 as per the new documentation
    connection = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"

    # CORRECTED: Initialize PGVector directly, passing the connection string
    store = PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=connection,
        use_jsonb=True, # Recommended for metadata filtering
    )
    return store

def process_and_store_document(document):
    """
    Takes a Document object, splits its content into chunks, creates embeddings,
    and stores them in the PGVector database.
    """
    print(f"Starting RAG processing for document ID: {document.id}...")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    docs = text_splitter.create_documents(
        [document.content],
        metadatas=[{"document_id": str(document.id)}]
    )

    vector_store = get_vector_store()

    # Use the add_documents method to store the chunks
    vector_store.add_documents(docs)

    print(f"Successfully processed and stored {len(docs)} chunks for document ID: {document.id}")
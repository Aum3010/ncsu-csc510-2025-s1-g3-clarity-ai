import os
import json
import re
from pydantic import ValidationError
from sqlalchemy import text

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from .prompts import get_requirements_generation_prompt, get_summary_generation_prompt
from .schemas import GeneratedRequirements, MeetingSummary
from .database_ops import save_requirements_to_db
# Import db and models for clearing tables and looping docs
from .main import db
from .models import Document, Requirement, Tag

COLLECTION_NAME = "document_chunks"

# --- NEW: Default query for automated requirement generation ---
DEFAULT_REQUIREMENTS_QUERY = """
Analyze the provided context and extract all functional requirements, non-functional requirements,
and user stories. For each item, provide a unique ID, a descriptive title, a detailed description,
an estimated priority (Low, Medium, High), and a status ('To Do').
Also include relevant tags (e.g., 'Security', 'UI/UX', 'Performance', 'Database').

Structure the output as a JSON object with a single "epics" key. Each epic should contain
a list of "user_stories", and each user story should have "story", "acceptance_criteria",
"priority", and "suggested_tags".
"""

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

# --- NEW: Function to delete document from RAG ---
def delete_document_from_rag(document_id: int):
    """
    Deletes all vector chunks associated with a specific document_id from PGVector.
    """
    print(f"Deleting document ID {document_id} from vector store...")
    try:
        vector_store = get_vector_store()
        
        # Get the collection ID
        collection_uuid = None
        with db.engine.connect() as conn:
            result = conn.execute(
                text("SELECT uuid FROM langchain_pg_collection WHERE name = :name"),
                {"name": COLLECTION_NAME}
            ).first()
            if result:
                collection_uuid = result[0]
        
        if not collection_uuid:
            print(f"Warning: Could not find collection '{COLLECTION_NAME}'. Skipping RAG deletion.")
            return

        # Delete embeddings based on cmetadata filter
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    """
                    DELETE FROM langchain_pg_embedding
                    WHERE collection_id = :collection_id
                    AND cmetadata->>'document_id' = :document_id
                    """
                ),
                {"collection_id": collection_uuid, "document_id": str(document_id)}
            )
            conn.commit()
        print(f"Successfully deleted chunks for document ID {document_id} from RAG.")

    except Exception as e:
        print(f"Error deleting document {document_id} from RAG: {e}")
        # We don't re-raise, as we want to allow DB deletion to proceed
        pass


def clean_llm_output(raw_output: str) -> str:
    """
    Cleans the raw LLM string output by removing markdown code fences
    and extracting only the JSON object.
    """
    match = re.search(r'```(json)?\s*(\{.*?\})\s*```', raw_output, re.DOTALL)
    if match:
        return match.group(2)
    return raw_output.strip()

def _run_rag_validation_loop(
    llm_prompt_func,
    validation_model,
    document_id: int | None = None, # MODIFIED: Now optional
    query: str | None = None
):
    """
    Internal helper to run the core RAG, Validation, and Retry loop.
    Accepts query as optional.
    If document_id is None, retrieves from all documents.
    """
    vector_store = get_vector_store()
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

    # --- MODIFIED: Conditional retriever ---
    retriever_kwargs = {}
    if document_id is not None:
        print(f"Scoping retriever to document_id: {document_id}")
        retriever_kwargs['search_kwargs'] = {'filter': {'document_id': str(document_id)}}
    else:
        print("Retriever is project-wide (all documents).")
        
    retriever = vector_store.as_retriever(**retriever_kwargs)
    # ---------------------------------------

    error_message = None
    max_retries = 2
    
    # Use a dummy query to retrieve context when running summarization
    rag_query_text = query if query is not None else "GENERATE SUMMARY AND ACTION ITEMS"

    for i in range(max_retries):
        print(f"Analysis attempt {i + 1}...")

        # 1. Prepare the arguments for the prompt function call
        prompt_kwargs = {
            "context": "{context}",
            "error_message": error_message
        }
        
        # Determine if we need to include {input} in the prompt
        if query is not None:
            prompt_kwargs["user_query"] = "{input}"
        
        # 2. Call the prompt function dynamically
        prompt_text = llm_prompt_func(**prompt_kwargs)
        prompt = ChatPromptTemplate.from_template(prompt_text)
        
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # 3. Define the LCEL chain
        # The chain starts with a dictionary that provides the 'input' (query text)
        rag_chain = (
            # Input starts as the text needed for the retriever
            RunnablePassthrough()
            # Map the original query to the 'input' key, and run the retriever for 'context'
            | {
                "context": retriever | format_docs, 
                "input": RunnablePassthrough() 
            }
            | prompt
            | llm
            | StrOutputParser()
        )
        
        # 4. Invoke the chain. We pass the rag_query_text (string) directly here.
        # LCEL automatically assigns this string to the input of the first runnable (RunnablePassthrough).
        raw_output = rag_chain.invoke(rag_query_text)

        try:
            cleaned_output = clean_llm_output(raw_output)
            validated_data = validation_model.model_validate_json(cleaned_output)
            print("LLM output cleaned and validated successfully!")
            return validated_data

        except (ValidationError, json.JSONDecodeError) as e:
            print(f"Validation failed on attempt {i + 1}: {e}")
            error_message = str(e)
            if i == max_retries - 1:
                raise Exception("Failed to generate valid JSON after multiple retries.") from e

    raise Exception("An unexpected error occurred in the analysis pipeline.")

# --- NEW: Helper for generating requirements for one doc ---
def generate_document_requirements(document_id: int):
    """
    Generates requirements for a SINGLE document using the default query.
    """
    print(f"Starting analysis for document ID: {document_id} with default query.")
    
    validated_data = _run_rag_validation_loop(
        llm_prompt_func=get_requirements_generation_prompt,
        validation_model=GeneratedRequirements,
        document_id=document_id,
        query=DEFAULT_REQUIREMENTS_QUERY
    )
    
    # Post-processing: Save to the database
    save_requirements_to_db(validated_data, document_id)
    return len(validated_data.epics) # Return count of epics, or you could sum user stories

# --- NEW: Project-wide requirements generation ---
def generate_project_requirements():
    """
    Generates requirements for ALL documents in the database.
    This clears all existing requirements first.
    """
    print("Starting project-wide requirements generation...")
    
    # 1. Clear existing requirements and tags
    print("Clearing old requirements and tags...")
    try:
        # Order of deletion matters if there are foreign key constraints
        # Delete from the association table first
        db.session.execute(text('DELETE FROM requirement_tags'))
        Requirement.query.delete()
        Tag.query.delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error clearing tables: {e}")
        raise
        
    # 2. Get all documents
    all_documents = Document.query.all()
    if not all_documents:
        print("No documents found to process.")
        return 0
        
    print(f"Found {len(all_documents)} documents to process...")
    total_generated = 0
    
    for doc in all_documents:
        try:
            count = generate_document_requirements(doc.id)
            total_generated += count
            print(f"Generated {count} requirement epics for document: {doc.filename}")
        except Exception as e:
            print(f"Failed to process document {doc.id} ({doc.filename}): {e}")
            # Continue to the next document
            pass
            
    print(f"Project-wide generation complete. Total new requirement epics: {total_generated}")
    return total_generated

def generate_project_summary():
    """
    Generates a single summary from ALL documents.
    """
    print(f"Starting project-wide summary generation...")

    validated_data = _run_rag_validation_loop(
        llm_prompt_func=get_summary_generation_prompt,
        validation_model=MeetingSummary,
        document_id=None,
        query=None 
    )
    
    output = f"Summary:\n{validated_data.summary}\n\n"
    output += "--- Key Decisions ---\n"
    output += "\n".join([f"- {d}" for d in validated_data.key_decisions])
    output += "\n\n--- Open Questions ---\n"
    output += "\n".join([f"- {q}" for q in validated_data.open_questions])
    output += "\n\n--- Action Items ---\n"
    for item in validated_data.action_items:
        output += f"- [ ] {item.task} (Assignee: {item.assignee or 'Unassigned'})\n"
        
    return output
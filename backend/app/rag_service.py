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

from .prompts import get_requirements_generation_prompt, get_summary_generation_prompt
from .schemas import GeneratedRequirements, MeetingSummary
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

def _run_rag_validation_loop(llm_prompt_func, validation_model, document_id, query: str | None = None):
    """
    Internal helper to run the core RAG, Validation, and Retry loop.
    Accepts query as optional, and uses conditional mapping to ensure correct LCEL input flow.
    """
    vector_store = get_vector_store()
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    retriever = vector_store.as_retriever(
        search_kwargs={'filter': {'document_id': str(document_id)}}
    )

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

# --- MAIN REQUIREMENT GENERATOR (RE-USES HELPER) ---
def analyze_document_and_generate_requirements(user_query: str, document_id: int):
    print(f"Starting analysis for document ID: {document_id} with query: '{user_query}'")
    
    validated_data = _run_rag_validation_loop(
        llm_prompt_func=get_requirements_generation_prompt,
        validation_model=GeneratedRequirements,
        document_id=document_id,
        query=user_query
    )
    
    # Post-processing: Save to the database
    save_requirements_to_db(validated_data, document_id)
    
    return "Analysis complete. Requirements have been generated and saved."

# --- NEW SUMMARY GENERATOR (RE-USES HELPER) ---
def generate_meeting_summary(document_id: int):
    print(f"Starting summary generation for document ID: {document_id}")
    
    # Query is explicitly omitted (passed as None). The dummy query text is handled inside the loop.
    validated_data = _run_rag_validation_loop(
        llm_prompt_func=get_summary_generation_prompt,
        validation_model=MeetingSummary,
        document_id=document_id,
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
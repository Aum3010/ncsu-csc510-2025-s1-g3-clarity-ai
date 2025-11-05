import pytest
from unittest.mock import MagicMock, patch, call, ANY
from pydantic import ValidationError
import threading

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import functions, models, schemas, AND create_app
from app import rag_service
from app.rag_service import (
    get_vector_store,
    process_and_store_document,
    delete_document_from_rag,
    _run_rag_validation_loop,
    generate_project_requirements,
    generate_project_summary
)
from app.models import Document, Requirement, ProjectSummary
from app.schemas import GeneratedRequirements, MeetingSummary
from app.main import create_app # <-- Import create_app

# --- Fixtures ---

@pytest.fixture(scope="module")
def app():
    """Provides a test Flask app context for the module."""
    test_app = create_app()
    test_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with test_app.app_context():
        yield test_app

@pytest.fixture(autouse=True)
def mock_env():
    """Mocks all required environment variables."""
    # Patch with app. prefix
    with patch('app.rag_service.os.getenv') as mock_getenv:
        mock_getenv.side_effect = lambda key, default=None: {
            "OPENAI_API_KEY": "test_key",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pw",
            "POSTGRES_HOST": "host",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "db"
        }.get(key, default)
        yield mock_getenv

@pytest.fixture(autouse=True)
def mock_db(app): # <-- Add app dependency
    """Mocks the global 'db' object and its session."""
    # Patch with app. prefix
    with patch('app.rag_service.db') as mock_db:
        mock_db.session = MagicMock()
        mock_db.engine.connect.return_value.__enter__.return_value = MagicMock()
        yield mock_db

#
# --- THIS IS THE CORRECTED FIXTURE ---
#
@pytest.fixture
def mock_langchain(app): # <-- Add app dependency
    """Mocks all LangChain components."""
    # Patch with app. prefix
    with patch('app.rag_service.OpenAIEmbeddings') as MockEmbeddings, \
         patch('app.rag_service.PGVector') as MockPGVector, \
         patch('app.rag_service.ChatOpenAI') as MockChatOpenAI, \
         patch('app.rag_service.RecursiveCharacterTextSplitter') as MockSplitter, \
         patch('app.rag_service.ChatPromptTemplate') as MockPromptTemplate, \
         patch('app.rag_service.RunnablePassthrough') as MockRunnablePassthrough, \
         patch('app.rag_service.StrOutputParser') as MockStrOutputParser:
        
        # Mock the vector store and retriever
        mock_vector_store = MockPGVector.return_value
        mock_retriever = MagicMock()
        mock_vector_store.as_retriever.return_value = mock_retriever
        
        # Mock components used by other tests
        mock_llm_inst = MockChatOpenAI.return_value
        mock_splitter_inst = MockSplitter.return_value
        mock_splitter_inst.create_documents.return_value = [MagicMock(page_content="chunk")]
        
        # --- THIS IS THE KEY FIX ---
        # Create a single mock to represent the FINAL chain
        mock_final_chain = MagicMock()
        mock_final_chain.invoke = MagicMock() # <-- This is critical
        
        # This simulates the entire chain of 4 | operations
        # RunnablePassthrough() | {...} | prompt | llm | StrOutputParser()
        MockRunnablePassthrough.return_value.__or__.return_value.__or__.return_value.__or__.return_value = mock_final_chain
        # --- END OF FIX ---

        yield {
            "PGVector": MockPGVector,
            "vector_store": mock_vector_store,
            "retriever": mock_retriever,
            "ChatOpenAI": MockChatOpenAI,
            "llm_instance": mock_llm_inst, # Keep for other tests
            "splitter": mock_splitter_inst,
            "final_chain": mock_final_chain # Yield the new chain mock
        }

@pytest.fixture
def mock_threading():
    """Mocks the threading.Thread class."""
    # Patch with app. prefix
    with patch('app.rag_service.threading.Thread') as mock_thread_cls:
        mock_thread_inst = MagicMock()
        mock_thread_cls.return_value = mock_thread_inst
        yield mock_thread_cls

# --- Test Cases ---

class TestRagService:

    def test_get_vector_store(self, mock_langchain):
        """Test vector store initialization."""
        store = get_vector_store()
        assert store == mock_langchain['vector_store']
        # Check that it was initialized with the correct connection string
        connection_str = "postgresql+psycopg://user:pw@host:5432/db"
        mock_langchain['PGVector'].assert_called_with(
            embeddings=ANY,
            collection_name="document_chunks",
            connection=connection_str,
            use_jsonb=True
        )

    def test_process_and_store_document_with_owner(self, mock_langchain, mock_threading):
        """Test document processing and background thread dispatch."""
        doc = Document(id=1, content="Test content", owner_id="user_123")
        
        # Patch with app. prefix
        with patch('app.rag_service.current_app') as mock_app:
            mock_app.app_context = MagicMock(return_value="fake_app_context")
            
            process_and_store_document(doc)
            
            # Verify text splitting
            mock_langchain['splitter'].create_documents.assert_called_with(
                ["Test content"],
                metadatas=[{"document_id": "1", "owner_id": "user_123"}]
            )
            # Verify adding to vector store
            mock_langchain['vector_store'].add_documents.assert_called_once()
            
            # Verify background thread was started
            mock_threading.return_value.start.assert_called_once()
            call_args = mock_threading.call_args
            assert call_args[1]['target'] == rag_service._run_summary_generation_in_background
            assert call_args[1]['args'] == ("fake_app_context", "user_123")

    def test_delete_document_from_rag(self, mock_db, mock_langchain):
        """Test deletion of document chunks from PGVector."""
        mock_conn = mock_db.engine.connect.return_value.__enter__.return_value
        
        # Mock finding the collection UUID
        mock_conn.execute.return_value.first.return_value = ("fake-uuid-123",)
        
        delete_document_from_rag(document_id=1)
        
        # Verify the text() calls
        calls = mock_conn.execute.call_args_list
        
        # 1. First call: get collection UUID
        assert "SELECT uuid FROM langchain_pg_collection" in str(calls[0][0][0])
        
        # 2. Second call: delete chunks
        delete_query = str(calls[1][0][0])
        assert "DELETE FROM langchain_pg_embedding" in delete_query
        assert "cmetadata->>'document_id' = :document_id" in delete_query
        
        # Check params passed to delete query
        delete_params = calls[1][0][1]
        assert delete_params['collection_id'] == "fake-uuid-123"
        assert delete_params['document_id'] == "1"

    # def test_run_rag_validation_loop_retry(self, mock_langchain):
    #     """Test the retry loop for validation."""
    #     mock_chain = mock_langchain['final_chain']
        
    #     bad_json = '{"epics": "not a list"}'
    #     good_json = '{"epics": [{"epic_name": "Test"}]}'
        
    #     mock_chain.invoke = MagicMock(side_effect=[bad_json, good_json])

    #     with patch('app.rag_service.GeneratedRequirements.model_validate_json') as mock_validate:
    #         mock_validate.side_effect = [
    #             ValidationError.from_exception_data("Error", []),
    #             GeneratedRequirements(epics=[]) # Success
    #         ]
            
    #         # Mock the prompt function
    #         mock_prompt_func = MagicMock(return_value="prompt text")
            
    #         _run_rag_validation_loop(
    #             llm_prompt_func=mock_prompt_func,
    #             validation_model=GeneratedRequirements,
    #             document_id=1,
    #             query="Test query",
    #             owner_id="user_1Example"
    #         )
            
    #         # Verify chain was called twice
    #         assert mock_chain.invoke.call_count == 2
            
    #         # Verify prompt function was called with error message on 2nd try
    #         prompt_calls = mock_prompt_func.call_args_list
    #         assert prompt_calls[0][1]['error_message'] is None
    #         assert prompt_calls[1][1]['error_message'] is not None

    def test_rag_loop_retriever_scoping(self, mock_langchain):
        """Test that the retriever is scoped correctly based on owner_id."""
        retriever = mock_langchain['retriever']
        store = mock_langchain['vector_store']
        
        # Patch the chain and validation to prevent execution
        # Patch with app. prefix
        with patch.object(GeneratedRequirements, 'model_validate_json'), \
             patch.object(rag_service, 'clean_llm_output', return_value="{}"):

            mock_prompt_func = MagicMock(return_value="prompt text")
            
            # Case 1: By owner_id
            _run_rag_validation_loop(mock_prompt_func, GeneratedRequirements, owner_id="user_123")
            store.as_retriever.assert_called_with(search_kwargs={'filter': {'owner_id': 'user_123'}})

            # Case 2: By document_id and owner_id
            _run_rag_validation_loop(mock_prompt_func, GeneratedRequirements, document_id=1, owner_id="user_123")
            store.as_retriever.assert_called_with(search_kwargs={'filter': {'document_id': '1', 'owner_id': 'user_123'}})

            # Case 3: Public (no owner, no doc)
            _run_rag_validation_loop(mock_prompt_func, GeneratedRequirements)
            store.as_retriever.assert_called_with(search_kwargs={'filter': {'owner_id': 'public'}})
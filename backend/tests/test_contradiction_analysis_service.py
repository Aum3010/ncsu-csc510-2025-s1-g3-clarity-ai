# test_contradiction_analysis_service.py

import pytest
from unittest.mock import MagicMock, patch, call
from pydantic import ValidationError
from datetime import datetime

# Import models and service to be tested
from app.models import Requirement, ContradictionAnalysis, ConflictingPair
from app.contradiction_analysis_service import (
    ContradictionAnalysisService, 
    ContradictionReportLLM
)

# --- Fixtures ---

@pytest.fixture
def mock_db():
    """Provides a MagicMock for the db instance."""
    db = MagicMock()
    db.session.query.return_value.filter.return_value.all.return_value = []
    db.session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    return db

@pytest.fixture
@patch('app.contradiction_analysis_service.ChatOpenAI')
def service(mock_chat_openai, mock_db):
    """
    Provides a ContradictionAnalysisService instance with mocked
    db and LLM client.
    """
    mock_llm_client = MagicMock()
    mock_chat_openai.return_value = mock_llm_client
    
    # Initialize the service
    service_instance = ContradictionAnalysisService(
        db_instance=mock_db, 
        user_id="test_user_123"
    )
    # Ensure the mocked client is attached
    service_instance.llm_client = mock_llm_client
    service_instance.llm_available = True
    return service_instance

@pytest.fixture
def mock_llm_chain():
    """Mocks the LangChain chain (prompt | llm | parser)."""
    mock_chain = MagicMock()
    # Patch the chain creation process
    with patch('app.contradiction_analysis_service.ChatPromptTemplate') as mock_prompt_template:
        # Mock the series of .__or__() calls
        mock_prompt_template.from_template.return_value.__or__.return_value.__or__.return_value = mock_chain
        yield mock_chain

# --- Test Cases ---

class TestContradictionAnalysisService:

    def test_init_llm_failure(self, mock_db):
        """Test service initialization when ChatOpenAI fails."""
        with patch('app.contradiction_analysis_service.ChatOpenAI', side_effect=Exception("API key error")):
            service_instance = ContradictionAnalysisService(mock_db, "test_user")
            assert service_instance.llm_available == False

    def test_invoke_llm_success_first_try(self, service, mock_llm_chain):
        """Test successful LLM invocation on the first attempt."""
        valid_json = '{"contradictions": [{"conflict_id": "C1", "reason": "Test", "conflicting_requirement_ids": ["R1", "R2"]}]}'
        mock_llm_chain.invoke.return_value = valid_json

        result = service._invoke_llm_with_retry("prompt", ContradictionReportLLM)

        assert result.contradictions[0].conflict_id == "C1"
        mock_llm_chain.invoke.assert_called_once()

    def test_invoke_llm_handles_markdown_fence(self, service, mock_llm_chain):
        """Test that it correctly parses JSON from a markdown code block."""
        json_with_fence = 'Here is the JSON: ```json\n{"contradictions": []}\n```'
        mock_llm_chain.invoke.return_value = json_with_fence
        
        result = service._invoke_llm_with_retry("prompt", ContradictionReportLLM)
        assert len(result.contradictions) == 0

    @patch('app.contradiction_analysis_service.get_json_correction_prompt')
    def test_run_analysis_no_requirements_raises_error(self, mock_fetch, service):
        """Test that ValueError is raised if no requirements are found."""
        mock_fetch.return_value = [] # No requirements
        
        with pytest.raises(ValueError, match="No requirements found"):
            service.run_analysis(document_id=1)


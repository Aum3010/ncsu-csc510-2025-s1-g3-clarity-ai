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

    def test_fetch_requirements(self, service, mock_db):
        """Test fetching and formatting requirements, including owner_id check."""
        # 1. Setup mock data
        req1 = Requirement(req_id="R-01", description="Must be fast.", owner_id="test_user_123")
        req2 = Requirement(req_id="R-02", title="Must be secure.", owner_id="test_user_123")
        
        # 2. Mock the query chain
        mock_query = mock_db.session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.all.return_value = [req1, req2]

        # 3. Action
        results = service._fetch_requirements(document_id=1)

        # 4. Assert
        # Check query was filtered by document_id AND owner_id
        mock_query.filter.assert_called_with(
            Requirement.source_document_id == 1,
            Requirement.owner_id == "test_user_123"
        )
        assert len(results) == 2
        assert results[0] == {"id": "R-01", "type": "UserStory", "text": "Must be fast."}
        # Check that it correctly uses title when description is missing
        assert results[1] == {"id": "R-02", "type": "Requirement", "text": "Must be secure."}

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
    def test_invoke_llm_retry_on_validation_error(self, mock_correction_prompt, service, mock_llm_chain):
        """Test the correction loop: fails validation once, then succeeds."""
        bad_json = '{"contradictions": "not a list"}'
        good_json = '{"contradictions": []}'
        
        # 1. First call returns bad JSON, second call returns good JSON
        mock_llm_chain.invoke.side_effect = [bad_json, good_json]
        
        # Mock the correction prompt generator
        mock_correction_prompt.return_value = "correction_prompt_template"

        result = service._invoke_llm_with_retry("initial_prompt", ContradictionReportLLM)

        # Assert successful empty result
        assert result.contradictions == []
        # Assert LLM was called twice
        assert mock_llm_chain.invoke.call_count == 2
        # Assert the correction prompt was generated
        mock_correction_prompt.assert_called_once_with(
            bad_json=bad_json,
            validation_error=str(ValidationError.from_json(bad_json).errors()[0])
        )

    def test_invoke_llm_max_retries_failure(self, service, mock_llm_chain):
        """Test that it fails gracefully (returns empty model) after max retries."""
        service.max_retries = 2
        invalid_json = '{"bad": "json"}' # Always invalid
        mock_llm_chain.invoke.return_value = invalid_json

        result = service._invoke_llm_with_retry("prompt", ContradictionReportLLM)
        
        # Should fail gracefully
        assert result.contradictions == []
        # 1 initial call + 2 retries = 3 calls
        assert mock_llm_chain.invoke.call_count == service.max_retries + 1

    def test_invoke_llm_api_error_failure(self, service, mock_llm_chain):
        """Test graceful failure on a non-validation error (e.g., API timeout)."""
        mock_llm_chain.invoke.side_effect = Exception("API Timeout")

        result = service._invoke_llm_with_retry("prompt", ContradictionReportLLM)
        
        assert result.contradictions == []
        mock_llm_chain.invoke.assert_called_once() # Fails on first attempt

    @patch('app.contradiction_analysis_service.ContradictionAnalysisService._fetch_requirements')
    @patch('app.contradiction_analysis_service.ContradictionAnalysisService._invoke_llm_with_retry')
    def test_run_analysis_with_conflicts(self, mock_invoke, mock_fetch, service, mock_db):
        """Test the full run_analysis flow where conflicts are found."""
        # 1. Setup fetch
        mock_fetch.return_value = [{"id": "R1", "text": "Test"}]
        
        # 2. Setup invoke
        llm_response = ContradictionReportLLM.model_validate_json(
            '{"contradictions": [{"conflict_id": "C1", "reason": "Test", "conflicting_requirement_ids": ["R1", "R2"]}]}'
        )
        mock_invoke.return_value = llm_response

        # 3. Run
        report = service.run_analysis(document_id=1)

        # 4. Verify report object
        assert report.total_conflicts_found == 1
        assert report.status == 'complete'
        assert report.owner_id == "test_user_123"
        
        # 5. Verify DB calls
        # Should add ContradictionAnalysis and ConflictingPair
        assert mock_db.session.add.call_count == 2
        mock_db.session.flush.assert_called_once()
        mock_db.session.commit.assert_called_once()
        
        # Check the objects saved
        saved_report = mock_db.session.add.call_args_list[0][0][0]
        assert isinstance(saved_report, ContradictionAnalysis)
        assert saved_report.source_document_id == 1
        
        saved_conflict = mock_db.session.add.call_args_list[1][0][0]
        assert isinstance(saved_conflict, ConflictingPair)
        assert saved_conflict.conflict_id == "C1"

    @patch('app.contradiction_analysis_service.ContradictionAnalysisService._fetch_requirements')
    @patch('app.contradiction_analysis_service.ContradictionAnalysisService._invoke_llm_with_retry')
    def test_run_analysis_no_conflicts(self, mock_invoke, mock_fetch, service, mock_db):
        """Test the full run_analysis flow where NO conflicts are found."""
        mock_fetch.return_value = [{"id": "R1", "text": "Test"}]
        mock_invoke.return_value = ContradictionReportLLM(contradictions=[]) # Empty list

        report = service.run_analysis(document_id=1)

        assert report.total_conflicts_found == 0
        assert report.status == 'no_conflicts'
        # Should only add the main report
        assert mock_db.session.add.call_count == 1
        mock_db.session.commit.assert_called_once()

    @patch('app.contradiction_analysis_service.ContradictionAnalysisService._fetch_requirements')
    def test_run_analysis_no_requirements_raises_error(self, mock_fetch, service):
        """Test that ValueError is raised if no requirements are found."""
        mock_fetch.return_value = [] # No requirements
        
        with pytest.raises(ValueError, match="No requirements found"):
            service.run_analysis(document_id=1)

    def test_get_latest_analysis(self, service, mock_db):
        """Test retrieving the latest analysis, including owner_id check."""
        mock_report = ContradictionAnalysis(id=5, analyzed_at=datetime.utcnow())
        
        mock_query = mock_db.session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order_by = mock_filter.order_by.return_value
        mock_order_by.first.return_value = mock_report

        result = service.get_latest_analysis(document_id=2)

        assert result == mock_report
        # Verify the security check
        mock_filter.assert_called_with(
            ContradictionAnalysis.source_document_id == 2,
            ContradictionAnalysis.owner_id == "test_user_123"
        )
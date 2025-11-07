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
        with patch('app.contradiction_analysis_service.StrOutputParser'):
            # Mock the series of .__or__() calls
            mock_prompt_template.from_template.return_value.__or__.return_value.__or__.return_value = mock_chain
            yield mock_chain

@pytest.fixture
def sample_requirements():
    """Provides sample requirement objects for testing."""
    req1 = MagicMock(spec=Requirement)
    req1.req_id = "R1"
    req1.description = "User must be able to login"
    req1.title = "Login Feature"
    
    req2 = MagicMock(spec=Requirement)
    req2.req_id = "R2"
    req2.description = None
    req2.title = "Disable authentication"
    
    req3 = MagicMock(spec=Requirement)
    req3.req_id = "R3"
    req3.description = "System should support dark mode"
    req3.title = "Dark Mode"
    
    return [req1, req2, req3]

# --- Test Cases ---

class TestContradictionAnalysisService:

    # --- Initialization Tests ---

    def test_init_llm_success(self, mock_db):
        """Test successful service initialization with LLM."""
        with patch('app.contradiction_analysis_service.ChatOpenAI') as mock_chat:
            service_instance = ContradictionAnalysisService(mock_db, "test_user")
            assert service_instance.llm_available == True
            assert service_instance.user_id == "test_user"
            assert service_instance.max_retries == 2
            mock_chat.assert_called_once_with(model="gpt-4o", max_retries=5, temperature=0.1)

    def test_init_llm_failure(self, mock_db):
        """Test service initialization when ChatOpenAI fails."""
        with patch('app.contradiction_analysis_service.ChatOpenAI', side_effect=Exception("API key error")):
            service_instance = ContradictionAnalysisService(mock_db, "test_user")
            assert service_instance.llm_available == False

    def test_init_without_user_id(self, mock_db):
        """Test initialization without a user_id."""
        with patch('app.contradiction_analysis_service.ChatOpenAI'):
            service_instance = ContradictionAnalysisService(mock_db)
            assert service_instance.user_id is None

    # --- Fetch Requirements Tests ---

    def test_fetch_requirements_returns_correct_format(self, service, sample_requirements):
        """Test that _fetch_requirements returns correctly formatted data."""
        service.db.session.query.return_value.filter.return_value.all.return_value = sample_requirements
        
        result = service._fetch_requirements(document_id=1)
        
        assert len(result) == 3
        assert result[0] == {"id": "R1", "type": "UserStory", "text": "User must be able to login"}
        assert result[1] == {"id": "R2", "type": "Requirement", "text": "Disable authentication"}
        assert result[2] == {"id": "R3", "type": "UserStory", "text": "System should support dark mode"}

    def test_fetch_requirements_empty_result(self, service):
        """Test _fetch_requirements when no requirements exist."""
        service.db.session.query.return_value.filter.return_value.all.return_value = []
        
        result = service._fetch_requirements(document_id=1)
        assert result == []

    def test_fetch_requirements_filters_by_user_id(self, service, sample_requirements):
        """Test that _fetch_requirements applies user_id filter."""
        service.db.session.query.return_value.filter.return_value.all.return_value = sample_requirements
        
        service._fetch_requirements(document_id=1)
        
        # Verify the query filters by source_document_id and owner_id
        assert service.db.session.query.called
        filter_call = service.db.session.query.return_value.filter
        assert filter_call.called

    # --- LLM Invocation Tests ---

    def test_invoke_llm_success_first_try(self, service, mock_llm_chain):
        """Test successful LLM invocation on the first attempt."""
        valid_json = '{"contradictions": [{"conflict_id": "C1", "reason": "Test", "conflicting_requirement_ids": ["R1", "R2"]}]}'
        mock_llm_chain.invoke.return_value = valid_json

        result = service._invoke_llm_with_retry("prompt", ContradictionReportLLM)

        assert len(result.contradictions) == 1
        assert result.contradictions[0].conflict_id == "C1"
        assert result.contradictions[0].reason == "Test"
        assert result.contradictions[0].conflicting_requirement_ids == ["R1", "R2"]
        mock_llm_chain.invoke.assert_called_once()

    def test_invoke_llm_handles_markdown_fence(self, service, mock_llm_chain):
        """Test that it correctly parses JSON from a markdown code block."""
        json_with_fence = 'Here is the JSON: ```json\n{"contradictions": []}\n```'
        mock_llm_chain.invoke.return_value = json_with_fence
        
        result = service._invoke_llm_with_retry("prompt", ContradictionReportLLM)
        assert len(result.contradictions) == 0

    def test_invoke_llm_handles_generic_fence(self, service, mock_llm_chain):
        """Test parsing JSON from generic code block fence."""
        json_with_fence = '```\n{"contradictions": []}\n```'
        mock_llm_chain.invoke.return_value = json_with_fence
        
        result = service._invoke_llm_with_retry("prompt", ContradictionReportLLM)
        assert len(result.contradictions) == 0

    @patch('app.contradiction_analysis_service.get_json_correction_prompt')
    def test_invoke_llm_retries_on_validation_error(self, mock_correction_prompt, service, mock_llm_chain):
        """Test that LLM invocation retries on validation error."""
        invalid_json = '{"contradictions": "not an array"}'
        valid_json = '{"contradictions": []}'
        
        mock_llm_chain.invoke.side_effect = [invalid_json, valid_json]
        mock_correction_prompt.return_value = "corrected prompt"
        
        result = service._invoke_llm_with_retry("initial prompt", ContradictionReportLLM)
        
        assert len(result.contradictions) == 0
        assert mock_llm_chain.invoke.call_count == 2
        mock_correction_prompt.assert_called_once()

    def test_invoke_llm_max_retries_returns_empty_model(self, service, mock_llm_chain):
        """Test that max retries returns empty model instead of crashing."""
        invalid_json = '{"contradictions": "invalid"}'
        mock_llm_chain.invoke.return_value = invalid_json
        
        result = service._invoke_llm_with_retry("prompt", ContradictionReportLLM)
        
        assert len(result.contradictions) == 0
        assert mock_llm_chain.invoke.call_count == 3  # Initial + 2 retries

    def test_invoke_llm_api_error_returns_empty_model(self, service, mock_llm_chain):
        """Test that API errors return empty model gracefully."""
        mock_llm_chain.invoke.side_effect = Exception("API timeout")
        
        result = service._invoke_llm_with_retry("prompt", ContradictionReportLLM)
        
        assert len(result.contradictions) == 0

    def test_invoke_llm_unavailable_raises_exception(self, service):
        """Test that invoking LLM when unavailable raises exception."""
        service.llm_available = False
        
        with pytest.raises(Exception, match="LLM client is not available"):
            service._invoke_llm_with_retry("prompt", ContradictionReportLLM)

    # --- Run Analysis Tests ---

    @patch('app.contradiction_analysis_service.get_contradiction_analysis_prompt')
    def test_run_analysis_no_requirements_raises_error(self, mock_prompt, service):
        """Test that ValueError is raised if no requirements are found."""
        service.db.session.query.return_value.filter.return_value.all.return_value = []
        
        with pytest.raises(ValueError, match="No requirements found"):
            service.run_analysis(document_id=1)

    @patch('app.contradiction_analysis_service.get_contradiction_analysis_prompt')
    def test_run_analysis_success_with_conflicts(self, mock_prompt, service, sample_requirements, mock_llm_chain):
        """Test successful analysis with conflicts found."""
        # Setup
        service.db.session.query.return_value.filter.return_value.all.return_value = sample_requirements
        mock_prompt.return_value = "analysis prompt"
        
        valid_json = '''{"contradictions": [
            {"conflict_id": "C1", "reason": "Login vs No Auth", "conflicting_requirement_ids": ["R1", "R2"]},
            {"conflict_id": "C2", "reason": "Theme conflict", "conflicting_requirement_ids": ["R2", "R3"]}
        ]}'''
        mock_llm_chain.invoke.return_value = valid_json
        
        # Execute
        result = service.run_analysis(document_id=1, project_context="Test project")
        
        # Verify
        assert isinstance(result, ContradictionAnalysis)
        assert result.source_document_id == 1
        assert result.owner_id == "test_user_123"
        assert result.total_conflicts_found == 2
        assert result.status == 'complete'
        assert service.db.session.add.call_count == 3  # 1 analysis + 2 conflicts
        assert service.db.session.commit.called

    @patch('app.contradiction_analysis_service.get_contradiction_analysis_prompt')
    def test_run_analysis_success_no_conflicts(self, mock_prompt, service, sample_requirements, mock_llm_chain):
        """Test successful analysis with no conflicts found."""
        service.db.session.query.return_value.filter.return_value.all.return_value = sample_requirements
        mock_prompt.return_value = "analysis prompt"
        mock_llm_chain.invoke.return_value = '{"contradictions": []}'
        
        result = service.run_analysis(document_id=1)
        
        assert result.total_conflicts_found == 0
        assert result.status == 'no_conflicts'
        assert service.db.session.add.call_count == 1  # Only analysis record

    @patch('app.contradiction_analysis_service.get_contradiction_analysis_prompt')
    def test_run_analysis_passes_project_context(self, mock_prompt, service, sample_requirements, mock_llm_chain):
        """Test that project context is passed to prompt generation."""
        service.db.session.query.return_value.filter.return_value.all.return_value = sample_requirements
        mock_llm_chain.invoke.return_value = '{"contradictions": []}'
        
        service.run_analysis(document_id=1, project_context="E-commerce platform")
        
        mock_prompt.assert_called_once()
        call_args = mock_prompt.call_args
        assert call_args[1]['project_context'] == "E-commerce platform"

    @patch('app.contradiction_analysis_service.get_contradiction_analysis_prompt')
    def test_run_analysis_creates_conflicting_pairs_correctly(self, mock_prompt, service, sample_requirements, mock_llm_chain):
        """Test that ConflictingPair records are created with correct attributes."""
        service.db.session.query.return_value.filter.return_value.all.return_value = sample_requirements
        mock_prompt.return_value = "prompt"
        
        valid_json = '''{"contradictions": [
            {"conflict_id": "C1", "reason": "Test conflict", "conflicting_requirement_ids": ["R1", "R2"]}
        ]}'''
        mock_llm_chain.invoke.return_value = valid_json
        
        # Mock flush to set an ID on the analysis object
        def set_analysis_id(obj):
            if isinstance(obj, ContradictionAnalysis):
                obj.id = 999
        service.db.session.add.side_effect = set_analysis_id
        
        service.run_analysis(document_id=1)
        
        # Verify ConflictingPair was created with correct data
        add_calls = service.db.session.add.call_args_list
        conflict_calls = [call for call in add_calls if isinstance(call[0][0], ConflictingPair)]
        assert len(conflict_calls) == 1

    # --- Get Latest Analysis Tests ---

    def test_get_latest_analysis_returns_most_recent(self, service):
        """Test that get_latest_analysis returns the most recent analysis."""
        mock_analysis = MagicMock(spec=ContradictionAnalysis)
        mock_analysis.id = 1
        mock_analysis.analyzed_at = datetime(2025, 1, 1)
        
        service.db.session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_analysis
        
        result = service.get_latest_analysis(document_id=1)
        
        assert result == mock_analysis
        assert service.db.session.query.called

    def test_get_latest_analysis_returns_none_when_no_analysis(self, service):
        """Test that get_latest_analysis returns None when no analysis exists."""
        service.db.session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        
        result = service.get_latest_analysis(document_id=1)
        
        assert result is None

    def test_get_latest_analysis_filters_by_user_id(self, service):
        """Test that get_latest_analysis filters by owner_id."""
        service.get_latest_analysis(document_id=1)
        
        # Verify query was called with filters
        assert service.db.session.query.called
        filter_call = service.db.session.query.return_value.filter
        assert filter_call.called

    # --- Edge Cases and Integration Tests ---

    @patch('app.contradiction_analysis_service.get_contradiction_analysis_prompt')
    def test_run_analysis_handles_complex_json_structure(self, mock_prompt, service, sample_requirements, mock_llm_chain):
        """Test handling of complex contradiction data."""
        service.db.session.query.return_value.filter.return_value.all.return_value = sample_requirements
        mock_prompt.return_value = "prompt"
        
        complex_json = '''{"contradictions": [
            {
                "conflict_id": "CONFLICT_001", 
                "reason": "Requirement R1 specifies authentication is mandatory, while R2 explicitly disables it",
                "conflicting_requirement_ids": ["R1", "R2", "R3"]
            }
        ]}'''
        mock_llm_chain.invoke.return_value = complex_json
        
        result = service.run_analysis(document_id=1)
        
        assert result.total_conflicts_found == 1
        assert result.status == 'complete'

    def test_service_isolation_between_users(self, mock_db):
        """Test that different users have isolated services."""
        with patch('app.contradiction_analysis_service.ChatOpenAI'):
            service1 = ContradictionAnalysisService(mock_db, "user1")
            service2 = ContradictionAnalysisService(mock_db, "user2")
            
            assert service1.user_id != service2.user_id
            assert service1.db == service2.db  # Same DB instance

    @patch('app.contradiction_analysis_service.get_contradiction_analysis_prompt')
    def test_run_analysis_commits_on_success(self, mock_prompt, service, sample_requirements, mock_llm_chain):
        """Test that database changes are committed on successful analysis."""
        service.db.session.query.return_value.filter.return_value.all.return_value = sample_requirements
        mock_prompt.return_value = "prompt"
        mock_llm_chain.invoke.return_value = '{"contradictions": []}'
        
        service.run_analysis(document_id=1)
        
        assert service.db.session.flush.called
        assert service.db.session.commit.called

    def test_multiple_fence_types_in_response(self, service, mock_llm_chain):
        """Test handling of response with multiple code fence types."""
        json_with_multiple_fences = '''Some text
        ```python
        code here
        ```
        Then the actual data:
        ```json
        {"contradictions": []}
        ```
        More text```'''
        mock_llm_chain.invoke.return_value = json_with_multiple_fences
        
        result = service._invoke_llm_with_retry("prompt", ContradictionReportLLM)
        assert len(result.contradictions) == 0
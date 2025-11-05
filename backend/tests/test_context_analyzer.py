import pytest
from unittest.mock import MagicMock, patch, call

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the class and validators to be tested/mocked
from app.context_analyzer import ContextAnalyzer
from app.validation_utils import InputSanitizer, LLMResponseValidator

# --- Fixtures ---

@pytest.fixture
def mock_llm_chain():
    """Mocks the full LangChain chain (Prompt | LLM | Parser)."""
    # Patch with app. prefix
    with patch('app.context_analyzer.ChatPromptTemplate') as mock_template:
        mock_chain = MagicMock()
        # Mock the chain creation "Prompt | LLM | Parser"
        mock_template.from_template.return_value.__or__.return_value.__or__.return_value = mock_chain
        yield mock_chain

@pytest.fixture
@patch('app.context_analyzer.ChatOpenAI') # Patch with app. prefix
def analyzer(mock_chat_openai):
    """Provides a ContextAnalyzer instance with a mocked LLM client."""
    mock_llm_client = MagicMock()
    mock_chat_openai.return_value = mock_llm_client
    return ContextAnalyzer(llm_client=mock_llm_client, batch_size=3, max_parallel=2)

@pytest.fixture(autouse=True)
def mock_validators():
    """Automatically mocks sanitizers and validators for all tests."""
    # Patch with app. prefix
    with patch('app.context_analyzer.InputSanitizer') as mock_sanitizer, \
         patch('app.context_analyzer.LLMResponseValidator') as mock_validator, \
         patch('app.context_analyzer.get_context_evaluation_prompt', return_value="mock prompt") as mock_prompt: # <-- ADD THIS
        
        # Passthrough sanitization
        mock_sanitizer.sanitize_for_llm_prompt.side_effect = lambda x: x
        
        # Passthrough validation
        mock_validator.validate_context_evaluation.side_effect = lambda d: d
        mock_validator.validate_batch_evaluation.side_effect = lambda l: l
        
        yield mock_sanitizer, mock_validator, mock_prompt

# --- Test Cases ---

class TestContextAnalyzer:

    def test_evaluate_term_in_context_success(self, analyzer, mock_llm_chain):
        """Test successful evaluation of a single term."""
        response_json = '{"is_ambiguous": false, "confidence": 0.9, "reasoning": "Clear"}'
        mock_llm_chain.invoke.return_value = response_json
        
        result = analyzer.evaluate_term_in_context("fast", "The system is fast.", "Context")
        
        assert result['is_ambiguous'] == False
        assert result['confidence'] == 0.9
        mock_llm_chain.invoke.assert_called_once()

    def test_evaluate_term_in_context_parse_failure(self, analyzer, mock_llm_chain):
        """Test fallback when LLM returns invalid JSON."""
        mock_llm_chain.invoke.return_value = "This is not JSON."
        
        # Mock the validator to raise an error
        # Patch with app. prefix
        with patch('app.context_analyzer.LLMResponseValidator.validate_context_evaluation', side_effect=ValueError("Bad JSON")):
            result = analyzer.evaluate_term_in_context("fast", "Sentence", "Context")

        # Should return conservative default
        assert result['is_ambiguous'] == True
        assert result['confidence'] == 0.5
        assert "Failed to parse" in result['reasoning']

    def test_evaluate_term_in_context_invoke_error(self, analyzer, mock_llm_chain):
        """Test fallback when the LLM chain itself fails."""
        mock_llm_chain.invoke.side_effect = Exception("API timeout")
        
        result = analyzer.evaluate_term_in_context("fast", "Sentence", "Context")
        
        assert result['is_ambiguous'] == True
        assert result['confidence'] == 0.5
        assert "Error during evaluation" in result['reasoning']

    def test_batch_evaluate_small_batch(self, analyzer):
        """Test that batch_evaluate calls optimized batch for small lists."""
        terms = [("fast", "s1", "c1"), ("easy", "s2", "c2")] # len 2 < batch_size 3
        
        with patch.object(analyzer, 'evaluate_batch_optimized') as mock_optimized:
            analyzer.batch_evaluate(terms)
            mock_optimized.assert_called_with(terms)

    def test_batch_evaluate_large_batch(self, analyzer):
        """Test that batch_evaluate calls parallel batch for large lists."""
        terms = [("fast", "s1", "c1")] * 5 # len 5 > batch_size 3
        
        with patch.object(analyzer, '_parallel_batch_evaluate') as mock_parallel:
            analyzer.batch_evaluate(terms)
            mock_parallel.assert_called_with(terms)

    def test_evaluate_batch_optimized_success(self, analyzer, mock_llm_chain):
        """Test the optimized single-call batch method."""
        terms = [("fast", "s1", "c1"), ("easy", "s2", "c2")]
        response_json = '[{"id":0, "is_ambiguous": true, "confidence": 0.8, "reasoning": "vague"}, {"id":1, "is_ambiguous": false, "confidence": 0.9, "reasoning": "clear"}]'        
        mock_llm_chain.invoke.return_value = response_json
        # Mock validator to return the expected number of results
        # Patch with app. prefix
        with patch('app.context_analyzer.LLMResponseValidator.validate_batch_evaluation') as mock_validate:
            mock_validate.return_value = [
                {"is_ambiguous": True, "confidence": 0.8, "reasoning": "vague"},
                {"is_ambiguous": False, "confidence": 0.9, "reasoning": "clear"}
            ]
            
            results = analyzer.evaluate_batch_optimized(terms)
        
        assert len(results) == 2
        assert results[0]['is_ambiguous'] == True
        assert results[1]['is_ambiguous'] == False
        mock_llm_chain.invoke.assert_called_once()
        assert analyzer.get_request_stats()['total_requests'] == 1

    def test_evaluate_batch_optimized_fallback(self, analyzer, mock_llm_chain):
        """Test fallback to sequential calls if optimized batch fails."""
        terms = [("fast", "s1", "c1"), ("easy", "s2", "c2")]
        
        # 1. Make the batch call fail
        mock_llm_chain.invoke.side_effect = Exception("Batch API error")
        
        # 2. Mock the fallback
        with patch.object(analyzer, '_fallback_sequential_evaluate') as mock_fallback:
            mock_fallback.return_value = ["fallback1", "fallback2"]
            
            results = analyzer.evaluate_batch_optimized(terms)
            
            assert results == ["fallback1", "fallback2"]
            mock_fallback.assert_called_with(terms)

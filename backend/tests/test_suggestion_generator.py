import pytest
from unittest.mock import MagicMock, patch, call

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the class and validators to be tested/mocked
from app.suggestion_generator import SuggestionGenerator
from app.validation_utils import InputSanitizer, LLMResponseValidator

# --- Fixtures ---

@pytest.fixture
def mock_llm_chain():
    """Mocks the full LangChain chain (Prompt | LLM | Parser)."""
    # Patch with app. prefix
    with patch('app.suggestion_generator.ChatPromptTemplate') as mock_template:
        mock_chain = MagicMock()
        mock_template.from_template.return_value.__or__.return_value.__or__.return_value = mock_chain
        yield mock_chain

@pytest.fixture
@patch('app.suggestion_generator.ChatOpenAI') # Patch with app. prefix
def generator(mock_chat_openai):
    """Provides a SuggestionGenerator instance with a mocked LLM client."""
    mock_llm_client = MagicMock()
    mock_chat_openai.return_value = mock_llm_client
    return SuggestionGenerator(llm_client=mock_llm_client, batch_size=3, max_parallel=2)

@pytest.fixture(autouse=True)
def mock_validators():
    """Automatically mocks sanitizers and validators for all tests."""
    # Patch with app. prefix
    with patch('app.suggestion_generator.InputSanitizer') as mock_sanitizer, \
         patch('app.suggestion_generator.LLMResponseValidator') as mock_validator:
        
        mock_sanitizer.sanitize_for_llm_prompt.side_effect = lambda x: x
        mock_validator.validate_suggestions.side_effect = lambda l: l
        mock_validator.validate_clarification_prompt.side_effect = lambda p: p
        
        yield mock_sanitizer, mock_validator

# --- Test Cases ---

class TestSuggestionGenerator:

    def test_generate_suggestions_success(self, generator, mock_llm_chain):
        """Test successful generation of suggestions."""
        response_json = '["suggestion 1", "suggestion 2"]'
        mock_llm_chain.invoke.return_value = response_json
        
        # Mock the parsing/validation
        with patch.object(generator, '_parse_suggestions_response', return_value=["s1", "s2"]) as mock_parse:
            results = generator.generate_suggestions("fast", "Context", "Sentence")
            assert results == ["s1", "s2"]
            mock_llm_chain.invoke.assert_called_once()
            mock_parse.assert_called_with(response_json)

    def test_generate_suggestions_failure(self, generator, mock_llm_chain):
        """Test fallback when LLM call fails."""
        mock_llm_chain.invoke.side_effect = Exception("API error")
        
        with patch.object(generator, '_get_fallback_suggestions') as mock_fallback:
            mock_fallback.return_value = ["fallback"]
            results = generator.generate_suggestions("fast", "Context", "Sentence")
            assert results == ["fallback"]
            mock_fallback.assert_called_with("fast")

    def test_generate_clarification_prompt_success(self, generator, mock_llm_chain, mock_validators):
        """Test successful generation of a clarification prompt."""
        _, mock_validator = mock_validators
        mock_llm_chain.invoke.return_value = "What do you mean by fast?"
        
        result = generator.generate_clarification_prompt("fast", "Context", "Sentence")
        
        assert result == "What do you mean by fast?"
        # Validator should be called
        mock_validator.validate_clarification_prompt.assert_called_with("What do you mean by fast?")

    def test_generate_complete_analysis_success(self, generator, mock_llm_chain):
        """Test the combined analysis call."""
        response_json = '{"suggestions": ["s1"], "clarification_prompt": "p1"}'
        mock_llm_chain.invoke.return_value = response_json
        
        with patch.object(generator, '_parse_complete_analysis_response') as mock_parse:
            mock_parse.return_value = {"suggestions": ["s1"], "clarification_prompt": "p1"}
            result = generator.generate_complete_analysis("fast", "Context", "Sentence")
            
            assert result["suggestions"] == ["s1"]
            assert result["clarification_prompt"] == "p1"
            mock_parse.assert_called_with(response_json)

    def test_batch_generate_small_batch(self, generator):
        """Test that batch_generate calls optimized batch for small lists."""
        terms = [("fast", "c1", "s1"), ("easy", "c2", "s2")] # len 2 < batch_size 3
        
        with patch.object(generator, '_batch_generate_optimized') as mock_optimized:
            generator.batch_generate_complete_analysis(terms)
            mock_optimized.assert_called_with(terms)

    def test_batch_generate_large_batch(self, generator):
        """Test that batch_generate calls parallel batch for large lists."""
        terms = [("fast", "c1", "s1")] * 5 # len 5 > batch_size 3
        
        with patch.object(generator, '_parallel_batch_generate') as mock_parallel:
            generator.batch_generate_complete_analysis(terms)
            mock_parallel.assert_called_with(terms)

    def test_batch_optimized_fallback(self, generator, mock_llm_chain):
        """Test fallback to individual calls if optimized batch fails."""
        terms = [("fast", "c1", "s1"), ("easy", "c2", "s2")]
        
        # 1. Make the batch call fail
        mock_llm_chain.invoke.side_effect = Exception("Batch API error")
        
        # 2. Mock the fallback
        with patch.object(generator, '_fallback_individual_generate') as mock_fallback:
            mock_fallback.return_value = ["fallback1", "fallback2"]
            
            results = generator._batch_generate_optimized(terms)
            
            assert results == ["fallback1", "fallback2"]
            mock_fallback.assert_called_with(terms)

    @patch('app.suggestion_generator.ThreadPoolExecutor') # Patch with app. prefix
    def test_parallel_batch_generate_chunk_failure(self, mock_executor_cls, generator):
        """Test parallel execution where one chunk fails."""
        terms = [("t1", "c1", "s1"), ("t2", "c2", "s2"), ("t3", "c3", "s3")]
        # Batch size is 3, so this is one chunk
        
        mock_executor = MagicMock()
        mock_executor_cls.return_value.__enter__.return_value = mock_executor
        
        # Mock 'as_completed' to return a future that raises an exception
        mock_future = MagicMock()
        mock_future.result.side_effect = Exception("Chunk error")

        # Patch with app. prefix
        with patch('app.suggestion_generator.as_completed', return_value=[mock_future]):
            chunk = terms[0:3]
            
            # This mapping is used by the real function
            future_map = { mock_future: (0, chunk) }
            mock_executor.submit.return_value = mock_future
            
            # Patch the internal 'future_to_chunk' map
            with patch.dict(generator._parallel_batch_generate.__globals__, {'future_to_chunk': future_map}):
                # Mock the fallback suggestion generator
                with patch.object(generator, '_get_fallback_suggestions') as mock_fallback:
                    mock_fallback.return_value = ["fallback"]
                    
                    results = generator._parallel_batch_generate(terms)
                    
                    # Should get 3 fallback results
                    assert len(results) == 3
                    assert results[0]['suggestions'] == ["fallback"]
                    assert "What specific criteria" in results[0]['clarification_prompt']

    def test_parse_complete_analysis_response(self, generator, mock_validators):
        """Test parsing of the combined analysis JSON."""
        _, mock_validator = mock_validators
        
        response_json = '{"suggestions": ["s1", "s2"], "clarification_prompt": "What?"}'
        result = generator._parse_complete_analysis_response(response_json)
        
        assert result['suggestions'] == ["s1", "s2"]
        assert result['clarification_prompt'] == "What?"
        mock_validator.validate_suggestions.assert_called_with(["s1", "s2"])
        mock_validator.validate_clarification_prompt.assert_called_with("What?")
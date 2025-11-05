import pytest

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all prompt functions
from app.prompts import (
    get_requirements_generation_prompt,
    get_summary_generation_prompt,
    get_context_evaluation_prompt,
    get_contradiction_analysis_prompt,
    get_json_correction_prompt
)

# --- Test Cases ---

class TestPromptGeneration:

    def test_requirements_prompt_no_error(self):
        """Test requirements prompt without an error message."""
        prompt = get_requirements_generation_prompt(
            context="Test context",
            user_query="Test query",
            error_message=None
        )
        assert "Test context" in prompt
        assert "Test query" in prompt
        assert "--- CORRECTION ---" not in prompt

    def test_requirements_prompt_with_error(self):
        """Test requirements prompt *with* an error message."""
        prompt = get_requirements_generation_prompt(
            context="Test context",
            user_query="Test query",
            error_message="Validation failed"
        )
        assert "Test context" in prompt
        assert "Test query" in prompt
        assert "--- CORRECTION ---" in prompt
        assert "Validation failed" in prompt

    def test_summary_prompt_with_error(self):
        """Test summary prompt *with* an error message."""
        prompt = get_summary_generation_prompt(
            context="Test context",
            error_message="Bad JSON"
        )
        assert "Test context" in prompt
        assert "--- CORRECTION ---" in prompt
        assert "Bad JSON" in prompt

    def test_contradiction_prompt_all_options(self):
        """Test contradiction prompt with context and error."""
        req_list = [{"id": "R1", "text": "Req 1"}]
        prompt = get_contradiction_analysis_prompt(
            requirements_json=req_list,
            project_context="Global context",
            error_message="Validation failed"
        )
        
        assert "ID: R1" in prompt
        assert "Req 1" in prompt
        assert "Global context" in prompt
        assert "--- CORRECTION ---" in prompt
        assert "Validation failed" in prompt

    def test_contradiction_prompt_minimal(self):
        """Test contradiction prompt with minimal inputs."""
        req_list = [{"id": "R1", "text": "Req 1"}]
        prompt = get_contradiction_analysis_prompt(
            requirements_json=req_list,
            project_context=None,
            error_message=None
        )
        
        assert "ID: R1" in prompt
        assert "--- CORRECTION ---" not in prompt

    def test_json_correction_prompt(self):
        """Test the JSON correction prompt."""
        prompt = get_json_correction_prompt(
            bad_json='{"key": "bad"}',
            validation_error="Invalid value"
        )
        
        assert "--- INVALID JSON ---" in prompt
        assert '{"key": "bad"}' in prompt
        assert "--- VALIDATION ERROR ---" in prompt
        assert "Invalid value" in prompt

    def test_context_evaluation_prompt_generation(self):
        """Test the context evaluation prompt."""
        # This function is simple, just check it returns a string
        # FIX: Pass a dummy string to satisfy the 'str' argument
        prompt = get_context_evaluation_prompt("dummy_str")
        assert isinstance(prompt, str)
        assert "Term to evaluate:" in prompt
        assert "is_ambiguous" in prompt
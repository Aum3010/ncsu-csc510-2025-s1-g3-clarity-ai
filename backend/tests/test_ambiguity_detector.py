import pytest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the detector, model, AND the create_app function
from app.ambiguity_detector import AmbiguityDetector
from app.models import Requirement
from app.main import create_app

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

@pytest.fixture
def mock_lexicon_manager():
    """Mocks the LexiconManager."""
    manager = MagicMock()
    # Import from app. prefix
    with patch('app.ambiguity_detector.LexiconManager') as mock_manager_class:
        manager = mock_manager_class.return_value
        manager.get_lexicon.return_value = ["fast", "easy", "secure"]
        yield manager

@pytest.fixture
def detector(mock_lexicon_manager):
    """Provides an AmbiguityDetector instance with a mocked manager."""
    return AmbiguityDetector(lexicon_manager=mock_lexicon_manager)

@pytest.fixture
def mock_db_query(app): # <-- Add app dependency
    """Mocks the Requirement.query chain."""
    # Patch with app. prefix
    with patch('app.ambiguity_detector.Requirement.query') as mock_query:
        mock_filter = MagicMock()
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = None
        yield mock_query, mock_filter

# --- Test Cases ---

class TestAmbiguityDetector:

    def test_segment_sentences(self, detector):
        """Test the sentence segmentation logic."""
        text = "This is sentence one. This is sentence two! And sentence three?\nFourth one."
        sentences = detector._segment_sentences(text)
        
        assert len(sentences) == 4
        assert sentences[0] == ("This is sentence one.", 0, 21)
        assert sentences[1] == ("This is sentence two!", 21, 43)
        assert sentences[2] == ("And sentence three?", 43, 64)
        assert sentences[3] == ("Fourth one.", 64, 75)

    def test_segment_sentences_no_punctuation(self, detector):
        """Test segmentation on text with no ending punctuation."""
        text = "This is a single sentence"
        sentences = detector._segment_sentences(text)
        assert len(sentences) == 1
        assert sentences[0] == ("This is a single sentence", 0, 25)

    def test_find_sentence_for_position(self, detector):
        """Test finding the correct sentence context for a position."""
        sentences = [
            ("Sentence one.", 0, 13),
            ("Sentence two.", 14, 27)
        ]
        # Position 5 is in "Sentence one."
        context = detector._find_sentence_for_position(5, sentences)
        assert context == "Sentence one."
        
        # Position 20 is in "Sentence two."
        context = detector._find_sentence_for_position(20, sentences)
        assert context == "Sentence two."

    def test_get_context_window(self, detector):
        """Test extracting a context window around a term."""
        text = "This is a long sentence that provides context for a term in the middle."
        # Term is "context" (pos 35-42)
        window = detector.get_context_window(text, 35, 42, window_size=20)
        
        expected = "...sentence that provides context for a term in th..."
        assert window == expected

    def test_get_context_window_at_start(self, detector):
        """Test context window at the beginning of the text."""
        text = "Term is at the start."
        # Term is "Term" (pos 0-4)
        window = detector.get_context_window(text, 0, 4, window_size=20)
        assert window == "Term is at the start." # No "..." at start

    def test_lexicon_scan_finds_terms(self, detector):
        """Test that the lexicon scan finds terms (case-insensitive, whole word)."""
        text = "The system must be FAST and easy. This is a fast-track, not fast."
        # Lexicon = ["fast", "easy", "secure"]
        
        flagged = detector._lexicon_scan(text, "user_123")
        
        assert len(flagged) == 4
        
        # Finds "FAST" (pos 19-23)
        assert flagged[0]['term'] == "FAST"
        assert flagged[0]['position_start'] == 19
        assert flagged[0]['sentence_context'] == "The system must be FAST and easy."
        
        # Finds "easy" (pos 28-32)
        assert flagged[1]['term'] == "easy"
        assert flagged[1]['position_start'] == 28
        assert flagged[1]['sentence_context'] == "The system must be FAST and easy."
        
        # Does NOT find "fast-track"

    def test_lexicon_scan_no_terms_found(self, detector):
        """Test scan on text with no matching lexicon terms."""
        text = "The system must be reliable and robust."
        flagged = detector._lexicon_scan(text, "user_123")
        assert len(flagged) == 0

    def test_analyze_text_empty(self, detector):
        """Test analyze_text with empty or None input."""
        result = detector.analyze_text("", "user_123")
        assert result['total_flagged'] == 0
        assert result['flagged_terms'] == []

    def test_analyze_requirement_success(self, detector, mock_db_query):
        """Test analyzing a requirement from the DB."""
        mock_query, mock_filter = mock_db_query
        
        # Mock the Requirement object
        req = Requirement(
            id=1,
            title="A fast system",
            description="It must be easy to use.",
            owner_id="user_123"
        )
        mock_filter.first.return_value = req
        
        result = detector.analyze_requirement(1, owner_id="user_123")
        
        # Verify query
        mock_query.filter_by.assert_called_with(id=1)
        mock_filter.first.assert_called_once()
        
        # Verify analysis on combined text: "A fast system\nIt must be easy to use."
        assert result['total_flagged'] == 2
        assert result['flagged_terms'][0]['term'] == "fast"
        assert result['flagged_terms'][1]['term'] == "easy"
        assert result['requirement_id'] == 1

    def test_analyze_requirement_not_found(self, detector, mock_db_query):
        """Test analysis when requirement ID doesn't exist."""
        mock_query, mock_filter = mock_db_query
        mock_filter.first.return_value = None # Not found
        
        with pytest.raises(ValueError, match="Requirement with ID 999 not found"):
            detector.analyze_requirement(999, owner_id="user_123")

    def test_analyze_requirement_access_denied(self, detector, mock_db_query):
        """Test analysis when owner_id does not match."""
        mock_query, mock_filter = mock_db_query
        
        # Mock a requirement owned by someone else
        req = Requirement(id=1, title="A fast system", owner_id="other_user")
        mock_filter.first.return_value = req
        
        with pytest.raises(ValueError, match="Access denied to requirement 1"):
            detector.analyze_requirement(1, owner_id="user_123")
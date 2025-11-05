import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the manager, model, AND the create_app function
from app.lexicon_manager import LexiconManager
from app.models import AmbiguityLexicon
from app.main import create_app

# --- Fixtures ---

@pytest.fixture(scope="module")
def app():
    """
    Creates a test Flask app context for the entire module.
    This fixture provides the "application context" needed by Flask-SQLAlchemy.
    """
    test_app = create_app()
    test_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", # Use in-memory db
    })
    
    # Push an application context before yielding
    with test_app.app_context():
        yield test_app # The context is active for all tests using this fixture

@pytest.fixture
def mock_lexicon_query(app): # <-- ADD 'app' FIXTURE DEPENDENCY
    """
    Mocks the AmbiguityLexicon.query object.
    This fixture now depends on 'app', so an app context is
    active *before* the patch() command runs.
    """
    # We patch the .query attribute on the model itself
    with patch('app.lexicon_manager.AmbiguityLexicon.query') as mock_query:
        # Configure the mock to return itself after .filter_by()
        # This allows chaining: .query.filter_by(...).all()
        mock_query.filter_by.return_value = mock_query
        
        # Set default return values (can be overridden in tests)
        mock_query.all.return_value = []
        mock_query.first.return_value = None
        yield mock_query

@pytest.fixture
def mock_db_session(app): # <-- ADD 'app' FIXTURE DEPENDENCY
    """
    Mocks the db.session object for add, delete, and commit operations.
    This also depends on the 'app' context.
    """
    with patch('app.lexicon_manager.db.session') as mock_session:
        yield mock_session

@pytest.fixture
def manager(mock_lexicon_query, mock_db_session):
    """
    Provides a fresh LexiconManager instance with a cleared cache
    and all DB interactions mocked.
    (This fixture implicitly depends on 'app' via its dependencies)
    """
    manager_instance = LexiconManager()
    manager_instance.clear_cache()
    yield manager_instance
    manager_instance.clear_cache() # Clear again after test

# --- Test Cases ---

class TestLexiconManager:

    def test_get_lexicon_global_only(self, manager, mock_lexicon_query):
        """Test fetching only global terms."""
        
        # Mock global terms
        global_terms = [
            AmbiguityLexicon(term="fast", type="global", owner_id=None),
            AmbiguityLexicon(term="easy", type="global", owner_id=None)
        ]
        # This is the only call .all() will make
        mock_lexicon_query.all.return_value = global_terms
        
        terms = manager.get_lexicon(owner_id=None)
        
        # Verify query
        # .filter_by() was called once, with these args
        mock_lexicon_query.filter_by.assert_called_with(type='global', owner_id=None)
        assert terms == ["easy", "fast"]

    def test_get_lexicon_with_user_terms(self, manager, mock_lexicon_query):
        """Test merging global, custom_include, and custom_exclude."""

        # Mock query results for different calls
        global_terms = [AmbiguityLexicon(term="fast"), AmbiguityLexicon(term="easy")]
        include_terms = [AmbiguityLexicon(term="simple")]
        exclude_terms = [AmbiguityLexicon(term="fast")] # User wants to exclude 'fast'

        # Use side_effect to return different values for each .all() call
        mock_lexicon_query.all.side_effect = [
            global_terms,   # Call for 'global'
            include_terms,  # Call for 'custom_include'
            exclude_terms   # Call for 'custom_exclude'
        ]

        terms = manager.get_lexicon(owner_id="user_123")

        # Verify query calls
        calls = [
            call(type='global', owner_id=None),
            call(type='custom_include', owner_id='user_123'),
            call(type='custom_exclude', owner_id='user_123')
        ]
        # Check that filter_by was called 3 times with these args
        mock_lexicon_query.filter_by.assert_has_calls(calls)
        
        # 'fast' is excluded, 'simple' is included
        assert terms == ["easy", "simple"]
        assert "fast" not in terms

    def test_get_lexicon_caching(self, manager, mock_lexicon_query):
        """Test that lexicon results are cached and reused."""
        
        global_terms = [AmbiguityLexicon(term="fast")]
        
        # Setup side_effect for the 3 calls in get_lexicon
        mock_lexicon_query.all.side_effect = [
            global_terms, # global
            [],           # include
            []            # exclude
        ]

        # 1. First call (should hit DB)
        terms1 = manager.get_lexicon(owner_id="user_123")
        assert terms1 == ["fast"]
        # .all() was called 3 times
        assert mock_lexicon_query.all.call_count == 3

        # 2. Second call (should use cache)
        terms2 = manager.get_lexicon(owner_id="user_123")
        assert terms2 == ["fast"]
        # Call count should NOT increase
        assert mock_lexicon_query.all.call_count == 3

    def test_add_term_invalidates_cache(self, manager, mock_lexicon_query, mock_db_session):
        """Test that adding a term invalidates the correct cache."""
        
        # Setup mocks for get_lexicon
        mock_lexicon_query.all.side_effect = [
            [AmbiguityLexicon(term="fast")], # global
            [], # include
            []  # exclude
        ]

        # 1. Cache the lexicon
        manager.get_lexicon(owner_id="user_123")
        assert "lexicon_user_123" in manager._cache
        assert manager._cache["lexicon_user_123"]["terms"] == ["fast"]

        # 2. Add a new term
        # Mock 'first' to return None (term doesn't exist)
        mock_lexicon_query.first.return_value = None 
        manager.add_term("new_term", owner_id="user_123", term_type="custom_include")

        # 3. Verify cache is invalidated
        assert "lexicon_user_123" not in manager._cache
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_remove_term_invalidates_cache(self, manager, mock_lexicon_query, mock_db_session):
        """Test that removing a term invalidates the cache."""
        
        # Setup mocks for get_lexicon
        mock_lexicon_query.all.side_effect = [
            [AmbiguityLexicon(term="fast")], # global
            [], # include
            []  # exclude
        ]

        # 1. Cache the lexicon
        manager.get_lexicon(owner_id="user_123")
        assert "lexicon_user_123" in manager._cache

        # 2. Remove a term
        term_to_remove = AmbiguityLexicon(term="fast")
        mock_lexicon_query.first.return_value = term_to_remove # Mock finding the term
        manager.remove_term("fast", owner_id="user_123", term_type="custom_include")

        # 3. Verify cache is invalidated
        assert "lexicon_user_123" not in manager._cache
        mock_db_session.delete.assert_called_with(term_to_remove)
        mock_db_session.commit.assert_called_once()

    def test_add_term_duplicate(self, manager, mock_lexicon_query, mock_db_session):
        """Test that adding a duplicate term returns False."""
        
        # Mock 'first' to return an existing term
        mock_lexicon_query.first.return_value = AmbiguityLexicon(term="fast")
        
        result = manager.add_term("fast", owner_id="user_123")
        
        assert result == False
        mock_db_session.add.assert_not_called()

    def test_remove_term_not_found(self, manager, mock_lexicon_query, mock_db_session):
        """Test that removing a non-existent term returns False."""
        
        # Mock 'first' to return None
        mock_lexicon_query.first.return_value = None
        
        result = manager.remove_term("non_existent", owner_id="user_123")
        
        assert result == False
        mock_db_session.delete.assert_not_called()

    def test_get_user_custom_terms(self, manager, mock_lexicon_query):
        """Test retrieving user's custom include/exclude lists."""

        include_terms = [AmbiguityLexicon(term="simple")]
        exclude_terms = [AmbiguityLexicon(term="fast")]

        mock_lexicon_query.all.side_effect = [include_terms, exclude_terms]

        result = manager.get_user_custom_terms(owner_id="user_123")

        calls = [
            call(type='custom_include', owner_id='user_123'),
            call(type='custom_exclude', owner_id='user_123')
        ]
        mock_lexicon_query.filter_by.assert_has_calls(calls)
        
        assert result['include'] == ["simple"]
        assert result['exclude'] == ["fast"]
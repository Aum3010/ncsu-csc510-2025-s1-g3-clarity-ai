"""
Lexicon Manager for Ambiguity Detection Engine

Manages the ambiguity lexicon with CRUD operations and user-specific scoping.
Includes caching layer for performance optimization.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .main import db
from .models import AmbiguityLexicon


class LexiconManager:
    """
    Manages the ambiguity lexicon with CRUD operations for lexicon terms.
    Supports user-specific lexicon scoping and caching.
    """
    
    # In-memory cache for lexicon data
    _cache: Dict[str, Dict] = {}
    _cache_ttl = timedelta(hours=1)  # Cache TTL of 1 hour
    
    def __init__(self):
        """Initialize the LexiconManager"""
        pass
    
    def get_lexicon(self, owner_id: Optional[str] = None) -> List[str]:
        """
        Get lexicon terms (global + user-specific).
        
        Args:
            owner_id: User ID for user-specific terms (optional)
            
        Returns:
            List of ambiguous terms to detect
        """
        cache_key = f"lexicon_{owner_id or 'global'}"
        
        # Check cache first
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if datetime.utcnow() - cached_data['timestamp'] < self._cache_ttl:
                return cached_data['terms']
        
        # Build lexicon from database
        terms = set()
        
        # Get global terms (type='global')
        global_terms = AmbiguityLexicon.query.filter_by(
            type='global',
            owner_id=None
        ).all()
        for term_obj in global_terms:
            terms.add(term_obj.term.lower())
        
        # Get user-specific terms if owner_id provided
        if owner_id:
            # Add custom_include terms
            custom_include = AmbiguityLexicon.query.filter_by(
                type='custom_include',
                owner_id=owner_id
            ).all()
            for term_obj in custom_include:
                terms.add(term_obj.term.lower())
            
            # Remove custom_exclude terms
            custom_exclude = AmbiguityLexicon.query.filter_by(
                type='custom_exclude',
                owner_id=owner_id
            ).all()
            for term_obj in custom_exclude:
                terms.discard(term_obj.term.lower())
        
        # Convert to sorted list
        result = sorted(list(terms))
        
        # Update cache
        self._cache[cache_key] = {
            'terms': result,
            'timestamp': datetime.utcnow()
        }
        
        return result
    
    def add_term(self, term: str, owner_id: Optional[str] = None, 
                 term_type: str = 'custom_include', category: Optional[str] = None) -> bool:
        """
        Add term to lexicon.
        
        Args:
            term: The term to add
            owner_id: User ID for user-specific terms (None for global)
            term_type: Type of term ('global', 'custom_include', 'custom_exclude')
            category: Optional category (e.g., 'performance', 'security')
            
        Returns:
            True if term was added, False if it already exists
        """
        term_lower = term.lower().strip()
        
        if not term_lower:
            return False
        
        # Check if term already exists
        existing = AmbiguityLexicon.query.filter_by(
            term=term_lower,
            type=term_type,
            owner_id=owner_id
        ).first()
        
        if existing:
            return False
        
        # Add new term
        new_term = AmbiguityLexicon(
            term=term_lower,
            type=term_type,
            owner_id=owner_id,
            category=category,
            added_at=datetime.utcnow()
        )
        
        db.session.add(new_term)
        db.session.commit()
        
        # Invalidate cache
        self._invalidate_cache(owner_id)
        
        return True
    
    def remove_term(self, term: str, owner_id: Optional[str] = None, 
                    term_type: str = 'custom_include') -> bool:
        """
        Remove term from lexicon.
        
        Args:
            term: The term to remove
            owner_id: User ID for user-specific terms (None for global)
            term_type: Type of term to remove
            
        Returns:
            True if term was removed, False if it didn't exist
        """
        term_lower = term.lower().strip()
        
        # Find and delete the term
        term_obj = AmbiguityLexicon.query.filter_by(
            term=term_lower,
            type=term_type,
            owner_id=owner_id
        ).first()
        
        if not term_obj:
            return False
        
        db.session.delete(term_obj)
        db.session.commit()
        
        # Invalidate cache
        self._invalidate_cache(owner_id)
        
        return True
    
    def get_default_lexicon(self) -> List[str]:
        """
        Get default ambiguous terms (global lexicon only).
        
        Returns:
            List of default ambiguous terms
        """
        return self.get_lexicon(owner_id=None)
    
    def get_user_custom_terms(self, owner_id: str) -> Dict[str, List[str]]:
        """
        Get user's custom lexicon terms (includes and excludes).
        
        Args:
            owner_id: User ID
            
        Returns:
            Dictionary with 'include' and 'exclude' lists
        """
        custom_include = AmbiguityLexicon.query.filter_by(
            type='custom_include',
            owner_id=owner_id
        ).all()
        
        custom_exclude = AmbiguityLexicon.query.filter_by(
            type='custom_exclude',
            owner_id=owner_id
        ).all()
        
        return {
            'include': [t.term for t in custom_include],
            'exclude': [t.term for t in custom_exclude]
        }
    
    def seed_default_lexicon(self) -> int:
        """
        Seed the database with default ambiguous terms.
        Only adds terms that don't already exist.
        
        Returns:
            Number of terms added
        """
        default_terms = [
            # Performance terms
            ('fast', 'performance'),
            ('slow', 'performance'),
            ('quick', 'performance'),
            ('efficient', 'performance'),
            ('responsive', 'performance'),
            ('performant', 'performance'),
            ('optimized', 'performance'),
            
            # Security terms
            ('secure', 'security'),
            ('safe', 'security'),
            ('protected', 'security'),
            
            # Usability terms
            ('user-friendly', 'usability'),
            ('easy', 'usability'),
            ('simple', 'usability'),
            ('intuitive', 'usability'),
            ('convenient', 'usability'),
            ('straightforward', 'usability'),
            
            # Quality terms
            ('robust', 'quality'),
            ('reliable', 'quality'),
            ('stable', 'quality'),
            ('scalable', 'quality'),
            ('maintainable', 'quality'),
            ('flexible', 'quality'),
            ('modular', 'quality'),
            
            # Appearance terms
            ('modern', 'appearance'),
            ('clean', 'appearance'),
            ('professional', 'appearance'),
            ('attractive', 'appearance'),
            
            # General vague terms
            ('good', 'general'),
            ('better', 'general'),
            ('best', 'general'),
            ('appropriate', 'general'),
            ('adequate', 'general'),
            ('reasonable', 'general'),
            ('sufficient', 'general'),
            ('acceptable', 'general'),
            ('normal', 'general'),
            ('typical', 'general'),
            ('standard', 'general'),
            ('regular', 'general'),
            ('common', 'general'),
            ('usual', 'general'),
        ]
        
        added_count = 0
        
        for term, category in default_terms:
            if self.add_term(term, owner_id=None, term_type='global', category=category):
                added_count += 1
        
        return added_count
    
    def _invalidate_cache(self, owner_id: Optional[str] = None):
        """
        Invalidate cache for a specific user or global cache.
        
        Args:
            owner_id: User ID to invalidate cache for (None for global)
        """
        cache_key = f"lexicon_{owner_id or 'global'}"
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        # Also invalidate global cache if user cache is invalidated
        if owner_id and 'lexicon_global' in self._cache:
            del self._cache['lexicon_global']
    
    def clear_cache(self):
        """Clear all cached lexicon data"""
        self._cache.clear()

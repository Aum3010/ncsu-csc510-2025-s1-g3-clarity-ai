"""
Ambiguity Detector for Ambiguity Detection Engine

Core detection engine that identifies ambiguous terms in text using lexicon-based
scanning and text segmentation.
"""

import re
from typing import List, Dict, Optional, Tuple
from .lexicon_manager import LexiconManager
from .models import Requirement
from .main import db


class AmbiguityDetector:
    """
    Core detection engine that identifies ambiguous terms in text.
    Uses lexicon-based scanning and text segmentation.
    """
    
    def __init__(self, lexicon_manager: LexiconManager):
        """
        Initialize with lexicon manager.
        
        Args:
            lexicon_manager: LexiconManager instance for accessing lexicon terms
        """
        self.lexicon_manager = lexicon_manager
    
    def analyze_text(self, text: str, owner_id: Optional[str] = None) -> Dict:
        """
        Analyze text for ambiguous terms.
        
        Args:
            text: Text to analyze
            owner_id: User ID for user-specific lexicon (optional)
            
        Returns:
            Dictionary containing:
                - original_text: The input text
                - flagged_terms: List of detected ambiguous terms with positions
                - total_flagged: Count of flagged terms
        """
        if not text or not text.strip():
            return {
                'original_text': text,
                'flagged_terms': [],
                'total_flagged': 0
            }
        
        # Perform lexicon scan
        flagged_terms = self._lexicon_scan(text, owner_id)
        
        return {
            'original_text': text,
            'flagged_terms': flagged_terms,
            'total_flagged': len(flagged_terms)
        }
    
    def analyze_requirement(self, requirement_id: int, owner_id: Optional[str] = None) -> Dict:
        """
        Analyze a specific requirement from database.
        
        Args:
            requirement_id: ID of the requirement to analyze
            owner_id: User ID for authorization and lexicon scoping
            
        Returns:
            Dictionary containing analysis results
            
        Raises:
            ValueError: If requirement not found or access denied
        """
        # Fetch requirement from database
        requirement = Requirement.query.filter_by(id=requirement_id).first()
        
        if not requirement:
            raise ValueError(f"Requirement with ID {requirement_id} not found")
        
        # Check authorization
        if owner_id and requirement.owner_id != owner_id:
            raise ValueError(f"Access denied to requirement {requirement_id}")
        
        # Combine title and description for analysis
        text_parts = [requirement.title]
        if requirement.description:
            text_parts.append(requirement.description)
        
        full_text = "\n".join(text_parts)
        
        # Analyze the text
        result = self.analyze_text(full_text, owner_id)
        result['requirement_id'] = requirement_id
        result['requirement'] = requirement
        
        return result
    
    def _lexicon_scan(self, text: str, owner_id: Optional[str] = None) -> List[Dict]:
        """
        Initial scan using predefined lexicon.
        Detects ambiguous terms and their positions in the text.
        
        Args:
            text: Text to scan
            owner_id: User ID for user-specific lexicon
            
        Returns:
            List of dictionaries containing term information:
                - term: The ambiguous term found
                - position_start: Start position in text
                - position_end: End position in text
                - sentence_context: The sentence containing the term
        """
        # Get lexicon terms
        lexicon_terms = self.lexicon_manager.get_lexicon(owner_id)
        
        if not lexicon_terms:
            return []
        
        # Segment text into sentences
        sentences = self._segment_sentences(text)
        
        flagged_terms = []
        
        # Search for each lexicon term in the text
        for term in lexicon_terms:
            # Create word boundary regex pattern for whole word matching
            # This prevents matching "fast" in "breakfast"
            pattern = r'\b' + re.escape(term) + r'\b'
            
            # Find all matches (case-insensitive)
            for match in re.finditer(pattern, text, re.IGNORECASE):
                position_start = match.start()
                position_end = match.end()
                matched_term = match.group()
                
                # Find the sentence containing this term
                sentence_context = self._find_sentence_for_position(
                    position_start, sentences
                )
                
                flagged_terms.append({
                    'term': matched_term,
                    'position_start': position_start,
                    'position_end': position_end,
                    'sentence_context': sentence_context
                })
        
        # Sort by position
        flagged_terms.sort(key=lambda x: x['position_start'])
        
        return flagged_terms
    
    def _segment_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Segment text into sentences with their positions.
        
        Args:
            text: Text to segment
            
        Returns:
            List of tuples (sentence, start_pos, end_pos)
        """
        # Simple sentence segmentation using regex
        # Matches sentences ending with . ! ? followed by space or end of string
        sentence_pattern = r'[^.!?\n]+[.!?\n]+'
        
        sentences = []
        for match in re.finditer(sentence_pattern, text):
            sentence = match.group().strip()
            if sentence:
                sentences.append((sentence, match.start(), match.end()))
        
        # Handle text that doesn't end with punctuation
        if sentences:
            last_end = sentences[-1][2]
            if last_end < len(text):
                remaining = text[last_end:].strip()
                if remaining:
                    sentences.append((remaining, last_end, len(text)))
        else:
            # No sentences found, treat entire text as one sentence
            if text.strip():
                sentences.append((text.strip(), 0, len(text)))
        
        return sentences
    
    def _find_sentence_for_position(self, position: int, 
                                   sentences: List[Tuple[str, int, int]]) -> str:
        """
        Find the sentence that contains a given position.
        
        Args:
            position: Character position in text
            sentences: List of (sentence, start_pos, end_pos) tuples
            
        Returns:
            The sentence containing the position
        """
        for sentence, start, end in sentences:
            if start <= position < end:
                return sentence
        
        # Fallback: return first sentence or empty string
        return sentences[0][0] if sentences else ""
    
    def get_context_window(self, text: str, position_start: int, 
                          position_end: int, window_size: int = 100) -> str:
        """
        Extract a context window around a term position.
        
        Args:
            text: Full text
            position_start: Start position of term
            position_end: End position of term
            window_size: Number of characters before and after (default: 100)
            
        Returns:
            Context string with the term and surrounding text
        """
        # Calculate window boundaries
        context_start = max(0, position_start - window_size)
        context_end = min(len(text), position_end + window_size)
        
        # Extract context
        context = text[context_start:context_end]
        
        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."
        
        return context.strip()

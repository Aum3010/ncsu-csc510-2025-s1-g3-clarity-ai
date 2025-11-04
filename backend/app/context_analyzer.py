"""
Context Analyzer for Ambiguity Detection Engine

LLM-powered context evaluation to determine if flagged terms are truly ambiguous
in their specific context.
"""

import json
import time
import asyncio
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .validation_utils import InputSanitizer, LLMResponseValidator
from .prompts import get_context_evaluation_prompt


class ContextAnalyzer:
    """
    LLM-powered context evaluation to determine if flagged terms are truly ambiguous.
    Uses GPT-4 to analyze terms in context and provide confidence scoring.
    """
    
    # Configuration for batch processing and rate limiting
    DEFAULT_BATCH_SIZE = 10  # Process up to 10 terms per API call
    MAX_PARALLEL_BATCHES = 3  # Maximum parallel batch requests
    MIN_REQUEST_INTERVAL = 0.1  # Minimum seconds between requests (10 req/sec)
    MAX_PROMPT_LENGTH = 4000  # Maximum characters per prompt to reduce tokens
    
    def __init__(self, llm_client: Optional[ChatOpenAI] = None, 
                 batch_size: int = None, max_parallel: int = None):
        """
        Initialize with LLM client.
        
        Args:
            llm_client: ChatOpenAI instance (creates default if None)
            batch_size: Number of terms to process per API call (default: 10)
            max_parallel: Maximum parallel batch requests (default: 3)
        """
        self.llm = llm_client or ChatOpenAI(model="gpt-4o", temperature=0.1)
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.max_parallel = max_parallel or self.MAX_PARALLEL_BATCHES
        self._last_request_time = 0
        self._request_count = 0
    
    def evaluate_term_in_context(self, term: str, sentence: str, 
                                 surrounding_context: Optional[str] = None) -> Dict:
        """
        Evaluate if a term is ambiguous in its specific context.
        
        Args:
            term: The term to evaluate
            sentence: The sentence containing the term
            surrounding_context: Additional context around the sentence (optional)
            
        Returns:
            Dictionary containing:
                - is_ambiguous: Boolean indicating if term is ambiguous
                - confidence: Float between 0 and 1
                - reasoning: String explaining the decision
        """
        # Sanitize inputs for LLM prompt
        try:
            sanitized_term = InputSanitizer.sanitize_for_llm_prompt(term)
            sanitized_sentence = InputSanitizer.sanitize_for_llm_prompt(sentence)
            sanitized_context = InputSanitizer.sanitize_for_llm_prompt(
                surrounding_context if surrounding_context else sentence
            )
        except ValueError as e:
            print(f"Input sanitization failed: {e}")
            return {
                'is_ambiguous': True,
                'confidence': 0.5,
                'reasoning': 'Invalid input detected'
            }
        
        prompt_template = get_context_evaluation_prompt()
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Build context string
        context_str = sanitized_sentence
        if sanitized_context and sanitized_context != sanitized_sentence:
            context_str = f"{sanitized_context}\n\nFocus sentence: {sanitized_sentence}"
        
        # Create chain
        chain = prompt | self.llm | StrOutputParser()
        
        # Invoke LLM
        try:
            response = chain.invoke({
                "term": sanitized_term,
                "context": context_str
            })
            
            # Parse and validate response
            result = self._parse_evaluation_response(response)
            return result
            
        except Exception as e:
            print(f"Error evaluating term '{term}': {e}")
            # Return conservative default (assume ambiguous)
            return {
                'is_ambiguous': True,
                'confidence': 0.5,
                'reasoning': f"Error during evaluation: {str(e)}"
            }
    
    def batch_evaluate(self, terms: List[Tuple[str, str, Optional[str]]]) -> List[Dict]:
        """
        Batch evaluation for processing multiple terms efficiently.
        Uses parallel processing for independent analyses.
        
        Args:
            terms: List of tuples (term, sentence, surrounding_context)
            
        Returns:
            List of evaluation dictionaries
        """
        if not terms:
            return []
        
        # For small batches, use optimized batch API call
        if len(terms) <= self.batch_size:
            return self.evaluate_batch_optimized(terms)
        
        # For larger batches, use parallel processing
        return self._parallel_batch_evaluate(terms)
    
    
    def _parse_evaluation_response(self, response: str) -> Dict:
        """
        Parse LLM response and validate structure.
        
        Args:
            response: Raw LLM response string
            
        Returns:
            Parsed evaluation dictionary
        """
        try:
            # Try to extract JSON from response
            # Handle markdown code blocks
            response = response.strip()
            if response.startswith("```"):
                # Extract JSON from code block
                lines = response.split("\n")
                json_lines = []
                in_code_block = False
                for line in lines:
                    if line.startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        json_lines.append(line)
                response = "\n".join(json_lines)
            
            # Parse JSON
            data = json.loads(response)
            
            # Validate using LLMResponseValidator
            validated = LLMResponseValidator.validate_context_evaluation(data)
            return validated
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response was: {response[:200]}")  # Only log first 200 chars
            # Return conservative default
            return {
                'is_ambiguous': True,
                'confidence': 0.5,
                'reasoning': f"Failed to parse LLM response: {str(e)}"
            }
    
    def evaluate_batch_optimized(self, terms: List[Tuple[str, str, Optional[str]]]) -> List[Dict]:
        """
        Optimized batch evaluation that sends multiple terms in a single API call.
        Includes rate limiting and prompt optimization.
        
        Args:
            terms: List of tuples (term, sentence, surrounding_context)
            
        Returns:
            List of evaluation dictionaries
        """
        if not terms:
            return []
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Build batch prompt with optimized context
        prompt_template = self._get_batch_evaluation_prompt()
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Format terms for batch processing with optimized context
        terms_list = []
        for idx, (term, sentence, context) in enumerate(terms):
            # Optimize context length to reduce tokens
            context_str = self._optimize_context(term, sentence, context)
            
            terms_list.append({
                'id': idx,
                'term': term,
                'context': context_str
            })
        
        # Create chain
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            # Optimize JSON formatting to reduce tokens
            terms_json = self._optimize_json_for_prompt(terms_list)
            
            response = chain.invoke({
                "terms_json": terms_json
            })
            
            # Track request
            self._request_count += 1
            
            # Parse batch response
            results = self._parse_batch_response(response, len(terms))
            return results
            
        except Exception as e:
            print(f"Error in batch evaluation: {e}")
            # Fallback to sequential individual evaluation
            return self._fallback_sequential_evaluate(terms)
    
    def _get_batch_evaluation_prompt(self) -> str:
        """
        Get the LLM prompt template for batch evaluation.
        Optimized for reduced token usage.
        
        Returns:
            Prompt template string
        """
        return """Evaluate if terms are ambiguous in context.

AMBIGUOUS: subjective, unmeasurable, open to interpretation
CLEAR: specific, measurable, well-defined, domain-specific technical term

Terms:
{terms_json}

Respond with JSON array (same order):
[{{"id":0,"is_ambiguous":true/false,"confidence":0.0-1.0,"reasoning":"1-2 sentences"}}]

Only JSON, no extra text."""
    
    def _parse_batch_response(self, response: str, expected_count: int) -> List[Dict]:
        """
        Parse batch LLM response.
        
        Args:
            response: Raw LLM response string
            expected_count: Expected number of results
            
        Returns:
            List of evaluation dictionaries
        """
        try:
            # Extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                json_lines = []
                in_code_block = False
                for line in lines:
                    if line.startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        json_lines.append(line)
                response = "\n".join(json_lines)
            
            # Parse JSON array
            data = json.loads(response)
            
            if not isinstance(data, list):
                raise ValueError("Response is not a JSON array")
            
            # Validate using LLMResponseValidator
            results = LLMResponseValidator.validate_batch_evaluation(data)
            
            # Ensure we have the expected number of results
            while len(results) < expected_count:
                results.append({
                    'is_ambiguous': True,
                    'confidence': 0.5,
                    'reasoning': 'Missing result from batch evaluation'
                })
            
            return results[:expected_count]
            
        except Exception as e:
            print(f"Error parsing batch response: {e}")
            # Return conservative defaults
            return [{
                'is_ambiguous': True,
                'confidence': 0.5,
                'reasoning': f"Failed to parse batch response: {str(e)}"
            }] * expected_count
    
    def _parallel_batch_evaluate(self, terms: List[Tuple[str, str, Optional[str]]]) -> List[Dict]:
        """
        Process large batches using parallel execution.
        
        Args:
            terms: List of tuples (term, sentence, surrounding_context)
            
        Returns:
            List of evaluation dictionaries in original order
        """
        # Split into chunks for parallel processing
        chunks = [
            terms[i:i + self.batch_size] 
            for i in range(0, len(terms), self.batch_size)
        ]
        
        results = [None] * len(terms)
        
        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            # Submit batch jobs
            future_to_chunk = {
                executor.submit(self.evaluate_batch_optimized, chunk): (idx, chunk)
                for idx, chunk in enumerate(chunks)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                chunk_idx, chunk = future_to_chunk[future]
                try:
                    chunk_results = future.result()
                    # Place results in correct position
                    start_idx = chunk_idx * self.batch_size
                    for i, result in enumerate(chunk_results):
                        results[start_idx + i] = result
                except Exception as e:
                    print(f"Error processing chunk {chunk_idx}: {e}")
                    # Fill with fallback results
                    start_idx = chunk_idx * self.batch_size
                    for i in range(len(chunk)):
                        results[start_idx + i] = {
                            'is_ambiguous': True,
                            'confidence': 0.5,
                            'reasoning': f"Error in parallel processing: {str(e)}"
                        }
        
        return results
    
    def _apply_rate_limit(self):
        """
        Apply rate limiting to prevent API quota exhaustion.
        Ensures minimum interval between requests.
        """
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.MIN_REQUEST_INTERVAL:
            sleep_time = self.MIN_REQUEST_INTERVAL - time_since_last
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def _optimize_context(self, term: str, sentence: str, 
                         context: Optional[str]) -> str:
        """
        Optimize context length to reduce token usage.
        
        Args:
            term: The term being evaluated
            sentence: The sentence containing the term
            context: Additional surrounding context
            
        Returns:
            Optimized context string
        """
        # If no additional context, just use sentence
        if not context or context == sentence:
            return sentence
        
        # If context is short enough, use it
        if len(context) <= self.MAX_PROMPT_LENGTH:
            return context
        
        # Find the sentence in the context and extract surrounding text
        try:
            sentence_pos = context.find(sentence)
            if sentence_pos == -1:
                # Sentence not found in context, just use sentence
                return sentence
            
            # Calculate how much context we can include
            max_before = (self.MAX_PROMPT_LENGTH - len(sentence)) // 2
            max_after = (self.MAX_PROMPT_LENGTH - len(sentence)) // 2
            
            start = max(0, sentence_pos - max_before)
            end = min(len(context), sentence_pos + len(sentence) + max_after)
            
            optimized = context[start:end]
            
            # Add ellipsis if truncated
            if start > 0:
                optimized = "..." + optimized
            if end < len(context):
                optimized = optimized + "..."
            
            return optimized
            
        except Exception as e:
            print(f"Error optimizing context: {e}")
            # Fallback to sentence only
            return sentence
    
    def _optimize_json_for_prompt(self, terms_list: List[Dict]) -> str:
        """
        Optimize JSON formatting to reduce token usage.
        
        Args:
            terms_list: List of term dictionaries
            
        Returns:
            Compact JSON string
        """
        # Use compact JSON formatting (no indentation)
        # Truncate long contexts if needed
        optimized_terms = []
        for term_data in terms_list:
            optimized = {
                'id': term_data['id'],
                'term': term_data['term'],
                'context': term_data['context'][:self.MAX_PROMPT_LENGTH]
            }
            optimized_terms.append(optimized)
        
        # Use compact JSON (no spaces)
        return json.dumps(optimized_terms, separators=(',', ':'))
    
    def _fallback_sequential_evaluate(self, terms: List[Tuple[str, str, Optional[str]]]) -> List[Dict]:
        """
        Fallback to sequential individual evaluation when batch fails.
        
        Args:
            terms: List of tuples (term, sentence, surrounding_context)
            
        Returns:
            List of evaluation dictionaries
        """
        results = []
        for term, sentence, context in terms:
            try:
                result = self.evaluate_term_in_context(term, sentence, context)
                results.append(result)
            except Exception as e:
                print(f"Error evaluating term '{term}': {e}")
                results.append({
                    'is_ambiguous': True,
                    'confidence': 0.5,
                    'reasoning': f"Error during evaluation: {str(e)}"
                })
        return results
    
    def get_request_stats(self) -> Dict:
        """
        Get statistics about API requests made.
        
        Returns:
            Dictionary with request statistics
        """
        return {
            'total_requests': self._request_count,
            'batch_size': self.batch_size,
            'max_parallel': self.max_parallel
        }

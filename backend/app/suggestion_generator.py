"""
Suggestion Generator for Ambiguity Detection Engine

Generates quantifiable replacements and clarification prompts for ambiguous terms
using LLM-based analysis.
"""

import json
import time
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .validation_utils import InputSanitizer, LLMResponseValidator


class SuggestionGenerator:
    """
    Generates quantifiable replacements and clarification prompts for ambiguous terms.
    Uses GPT-4 to create context-appropriate suggestions.
    """
    
    # Configuration for batch processing and rate limiting
    DEFAULT_BATCH_SIZE = 8  # Process up to 8 terms per API call
    MAX_PARALLEL_BATCHES = 3  # Maximum parallel batch requests
    MIN_REQUEST_INTERVAL = 0.1  # Minimum seconds between requests
    MAX_CONTEXT_LENGTH = 3000  # Maximum context length to reduce tokens
    
    def __init__(self, llm_client: Optional[ChatOpenAI] = None,
                 batch_size: int = None, max_parallel: int = None):
        """
        Initialize with LLM client.
        
        Args:
            llm_client: ChatOpenAI instance (creates default if None)
            batch_size: Number of terms to process per API call (default: 8)
            max_parallel: Maximum parallel batch requests (default: 3)
        """
        self.llm = llm_client or ChatOpenAI(model="gpt-4o", temperature=0.3)
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.max_parallel = max_parallel or self.MAX_PARALLEL_BATCHES
        self._last_request_time = 0
        self._request_count = 0
    
    def generate_suggestions(self, term: str, context: str, 
                           sentence: Optional[str] = None) -> List[str]:
        """
        Generate 2-3 specific replacement suggestions.
        
        Args:
            term: The ambiguous term to replace
            context: The context containing the term
            sentence: The specific sentence containing the term (optional)
            
        Returns:
            List of 2-3 suggested replacements with quantifiable metrics
        """
        # Sanitize inputs for LLM prompt
        try:
            sanitized_term = InputSanitizer.sanitize_for_llm_prompt(term)
            sanitized_context = InputSanitizer.sanitize_for_llm_prompt(context)
            sanitized_sentence = InputSanitizer.sanitize_for_llm_prompt(
                sentence if sentence else context
            )
        except ValueError as e:
            print(f"Input sanitization failed: {e}")
            return self._get_fallback_suggestions(term)
        
        prompt_template = self._get_suggestion_prompt()
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Create chain
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            response = chain.invoke({
                "term": sanitized_term,
                "context": sanitized_context,
                "sentence": sanitized_sentence
            })
            
            # Parse and validate response
            suggestions = self._parse_suggestions_response(response)
            return suggestions
            
        except Exception as e:
            print(f"Error generating suggestions for '{term}': {e}")
            # Return generic fallback suggestions
            return self._get_fallback_suggestions(term)
    
    def generate_clarification_prompt(self, term: str, context: str,
                                     sentence: Optional[str] = None) -> str:
        """
        Generate user-friendly clarification question.
        
        Args:
            term: The ambiguous term
            context: The context containing the term
            sentence: The specific sentence containing the term (optional)
            
        Returns:
            User-friendly clarification question
        """
        # Sanitize inputs for LLM prompt
        try:
            sanitized_term = InputSanitizer.sanitize_for_llm_prompt(term)
            sanitized_context = InputSanitizer.sanitize_for_llm_prompt(context)
            sanitized_sentence = InputSanitizer.sanitize_for_llm_prompt(
                sentence if sentence else context
            )
        except ValueError as e:
            print(f"Input sanitization failed: {e}")
            return f"What specific, measurable criteria do you mean by '{term}'?"
        
        prompt_template = self._get_clarification_prompt_template()
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Create chain
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            response = chain.invoke({
                "term": sanitized_term,
                "context": sanitized_context,
                "sentence": sanitized_sentence
            })
            
            # Validate and clean the prompt
            clarification = LLMResponseValidator.validate_clarification_prompt(response)
            return clarification
            
        except Exception as e:
            print(f"Error generating clarification prompt for '{term}': {e}")
            # Return generic fallback
            return f"What specific, measurable criteria do you mean by '{term}'?"
    
    def generate_complete_analysis(self, term: str, context: str,
                                  sentence: Optional[str] = None) -> Dict:
        """
        Generate both suggestions and clarification prompt in one call.
        
        Args:
            term: The ambiguous term
            context: The context containing the term
            sentence: The specific sentence containing the term (optional)
            
        Returns:
            Dictionary containing:
                - suggestions: List of replacement suggestions
                - clarification_prompt: User-friendly question
        """
        prompt_template = self._get_complete_analysis_prompt()
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Use sentence if provided, otherwise use full context
        focus_text = sentence if sentence else context
        
        # Create chain
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            response = chain.invoke({
                "term": term,
                "context": context,
                "sentence": focus_text
            })
            
            # Parse response
            result = self._parse_complete_analysis_response(response)
            return result
            
        except Exception as e:
            print(f"Error generating complete analysis for '{term}': {e}")
            # Return fallback
            return {
                'suggestions': self._get_fallback_suggestions(term),
                'clarification_prompt': f"What specific, measurable criteria do you mean by '{term}'?"
            }
    
    def _get_suggestion_prompt(self) -> str:
        """
        Get the LLM prompt template for generating suggestions.
        
        Returns:
            Prompt template string
        """
        return """You are an expert in software requirements engineering. Your task is to suggest specific, quantifiable replacements for an ambiguous term.

Ambiguous term: "{term}"

Full context:
{context}

Sentence containing the term:
{sentence}

Generate 2-3 specific, measurable alternatives that could replace the ambiguous term "{term}" in this context.

Requirements for suggestions:
- Each suggestion must be specific and quantifiable
- Include concrete metrics, numbers, or measurable criteria
- Be realistic and appropriate for the context
- Use industry-standard terminology where applicable
- Each suggestion should be a complete phrase that can replace the term

Respond with a JSON array of strings:
[
    "suggestion 1 with specific metrics",
    "suggestion 2 with specific metrics",
    "suggestion 3 with specific metrics"
]

Examples:
- Instead of "fast": "response time under 200ms", "load time under 2 seconds"
- Instead of "secure": "encrypted with AES-256", "compliant with OWASP Top 10"
- Instead of "user-friendly": "learnable within 30 minutes", "requires no more than 3 clicks"

Respond ONLY with the JSON array, no additional text."""
    
    def _get_clarification_prompt_template(self) -> str:
        """
        Get the LLM prompt template for generating clarification questions.
        
        Returns:
            Prompt template string
        """
        return """You are an expert in software requirements engineering. Your task is to create a user-friendly question that helps clarify an ambiguous term.

Ambiguous term: "{term}"

Full context:
{context}

Sentence containing the term:
{sentence}

Generate a clear, friendly question that asks the user to specify what they mean by "{term}" in this context.

Requirements for the question:
- Use simple, non-technical language
- Be specific to the context
- Guide the user toward providing measurable criteria
- Be conversational and friendly
- Keep it concise (1-2 sentences)

Examples:
- "What specific response time do you consider 'fast' for this feature?"
- "What security standards or certifications should the system meet?"
- "How would you measure whether the interface is 'user-friendly'?"

Respond with ONLY the question text, no quotes or additional formatting."""
    
    def _get_complete_analysis_prompt(self) -> str:
        """
        Get the LLM prompt template for complete analysis (suggestions + prompt).
        
        Returns:
            Prompt template string
        """
        return """You are an expert in software requirements engineering. Your task is to help clarify an ambiguous term by providing both specific suggestions and a clarification question.

Ambiguous term: "{term}"

Full context:
{context}

Sentence containing the term:
{sentence}

Provide:
1. 2-3 specific, measurable alternatives for "{term}"
2. A user-friendly question to help clarify what they mean

Respond with a JSON object:
{{
    "suggestions": [
        "suggestion 1 with specific metrics",
        "suggestion 2 with specific metrics",
        "suggestion 3 with specific metrics"
    ],
    "clarification_prompt": "Your friendly question here"
}}

Requirements:
- Suggestions must be specific and quantifiable
- Question should be conversational and guide toward measurable criteria
- Be appropriate for the context

Respond ONLY with the JSON object, no additional text."""
    
    def _parse_suggestions_response(self, response: str) -> List[str]:
        """
        Parse LLM response for suggestions.
        
        Args:
            response: Raw LLM response string
            
        Returns:
            List of suggestion strings
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
            suggestions = json.loads(response)
            
            # Validate using LLMResponseValidator
            validated = LLMResponseValidator.validate_suggestions(suggestions)
            return validated[:3]  # Return max 3 suggestions
            
        except Exception as e:
            print(f"Error parsing suggestions response: {e}")
            return self._get_fallback_suggestions("")
    
    def _parse_complete_analysis_response(self, response: str) -> Dict:
        """
        Parse LLM response for complete analysis.
        
        Args:
            response: Raw LLM response string
            
        Returns:
            Dictionary with suggestions and clarification_prompt
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
            
            # Parse JSON object
            data = json.loads(response)
            
            suggestions = data.get('suggestions', [])
            clarification_prompt = data.get('clarification_prompt', '')
            
            # Validate using LLMResponseValidator
            try:
                validated_suggestions = LLMResponseValidator.validate_suggestions(suggestions)
            except ValueError:
                validated_suggestions = self._get_fallback_suggestions("")
            
            try:
                validated_prompt = LLMResponseValidator.validate_clarification_prompt(clarification_prompt)
            except ValueError:
                validated_prompt = "What specific, measurable criteria do you mean by this term?"
            
            return {
                'suggestions': validated_suggestions[:3],
                'clarification_prompt': validated_prompt
            }
            
        except Exception as e:
            print(f"Error parsing complete analysis response: {e}")
            return {
                'suggestions': self._get_fallback_suggestions(""),
                'clarification_prompt': "What specific, measurable criteria do you mean by this term?"
            }
    
    def _get_fallback_suggestions(self, term: str) -> List[str]:
        """
        Get generic fallback suggestions when LLM fails.
        
        Args:
            term: The ambiguous term
            
        Returns:
            List of generic suggestions
        """
        # Generic suggestions based on common patterns
        return [
            f"Define specific metrics or thresholds for '{term}'",
            f"Specify measurable criteria for '{term}'",
            f"Provide quantifiable requirements for '{term}'"
        ]
    
    def batch_generate_complete_analysis(self, 
                                        terms_data: List[Tuple[str, str, Optional[str]]]) -> List[Dict]:
        """
        Generate complete analysis (suggestions + prompts) for multiple terms efficiently.
        Uses batch processing and parallel execution.
        
        Args:
            terms_data: List of tuples (term, context, sentence)
            
        Returns:
            List of dictionaries with 'suggestions' and 'clarification_prompt'
        """
        if not terms_data:
            return []
        
        # For small batches, use single API call
        if len(terms_data) <= self.batch_size:
            return self._batch_generate_optimized(terms_data)
        
        # For larger batches, use parallel processing
        return self._parallel_batch_generate(terms_data)
    
    def _batch_generate_optimized(self, 
                                  terms_data: List[Tuple[str, str, Optional[str]]]) -> List[Dict]:
        """
        Generate analysis for multiple terms in a single API call.
        
        Args:
            terms_data: List of tuples (term, context, sentence)
            
        Returns:
            List of analysis dictionaries
        """
        if not terms_data:
            return []
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Build batch prompt
        prompt_template = self._get_batch_complete_analysis_prompt()
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Format terms for batch processing
        terms_list = []
        for idx, (term, context, sentence) in enumerate(terms_data):
            # Optimize context length
            optimized_context = self._optimize_context(context, sentence)
            
            terms_list.append({
                'id': idx,
                'term': term,
                'context': optimized_context,
                'sentence': sentence if sentence else optimized_context
            })
        
        # Create chain
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            # Use compact JSON
            terms_json = json.dumps(terms_list, separators=(',', ':'))
            
            response = chain.invoke({
                "terms_json": terms_json
            })
            
            # Track request
            self._request_count += 1
            
            # Parse batch response
            results = self._parse_batch_complete_analysis(response, len(terms_data))
            return results
            
        except Exception as e:
            print(f"Error in batch suggestion generation: {e}")
            # Fallback to individual generation
            return self._fallback_individual_generate(terms_data)
    
    def _parallel_batch_generate(self, 
                                terms_data: List[Tuple[str, str, Optional[str]]]) -> List[Dict]:
        """
        Process large batches using parallel execution.
        
        Args:
            terms_data: List of tuples (term, context, sentence)
            
        Returns:
            List of analysis dictionaries in original order
        """
        # Split into chunks
        chunks = [
            terms_data[i:i + self.batch_size]
            for i in range(0, len(terms_data), self.batch_size)
        ]
        
        results = [None] * len(terms_data)
        
        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            future_to_chunk = {
                executor.submit(self._batch_generate_optimized, chunk): (idx, chunk)
                for idx, chunk in enumerate(chunks)
            }
            
            for future in as_completed(future_to_chunk):
                chunk_idx, chunk = future_to_chunk[future]
                try:
                    chunk_results = future.result()
                    start_idx = chunk_idx * self.batch_size
                    for i, result in enumerate(chunk_results):
                        results[start_idx + i] = result
                except Exception as e:
                    print(f"Error processing suggestion chunk {chunk_idx}: {e}")
                    start_idx = chunk_idx * self.batch_size
                    for i, (term, _, _) in enumerate(chunk):
                        results[start_idx + i] = {
                            'suggestions': self._get_fallback_suggestions(term),
                            'clarification_prompt': f"What specific criteria do you mean by '{term}'?"
                        }
        
        return results
    
    def _apply_rate_limit(self):
        """Apply rate limiting to prevent API quota exhaustion."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.MIN_REQUEST_INTERVAL:
            sleep_time = self.MIN_REQUEST_INTERVAL - time_since_last
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def _optimize_context(self, context: str, sentence: Optional[str]) -> str:
        """
        Optimize context length to reduce token usage.
        
        Args:
            context: Full context
            sentence: Specific sentence (optional)
            
        Returns:
            Optimized context string
        """
        if not context:
            return sentence or ""
        
        if len(context) <= self.MAX_CONTEXT_LENGTH:
            return context
        
        # If we have a sentence, try to keep context around it
        if sentence and sentence in context:
            sentence_pos = context.find(sentence)
            max_before = (self.MAX_CONTEXT_LENGTH - len(sentence)) // 2
            max_after = (self.MAX_CONTEXT_LENGTH - len(sentence)) // 2
            
            start = max(0, sentence_pos - max_before)
            end = min(len(context), sentence_pos + len(sentence) + max_after)
            
            optimized = context[start:end]
            if start > 0:
                optimized = "..." + optimized
            if end < len(context):
                optimized = optimized + "..."
            
            return optimized
        
        # Otherwise, just truncate
        return context[:self.MAX_CONTEXT_LENGTH] + "..."
    
    def _get_batch_complete_analysis_prompt(self) -> str:
        """
        Get optimized prompt for batch suggestion generation.
        
        Returns:
            Prompt template string
        """
        return """Generate suggestions and clarification questions for ambiguous terms.

Terms:
{terms_json}

For each term, provide 2-3 specific, measurable alternatives and a friendly question.

Respond with JSON array (same order):
[{{"id":0,"suggestions":["specific metric 1","specific metric 2"],"clarification_prompt":"Your question?"}}]

Only JSON, no extra text."""
    
    def _parse_batch_complete_analysis(self, response: str, expected_count: int) -> List[Dict]:
        """
        Parse batch response for complete analysis.
        
        Args:
            response: Raw LLM response
            expected_count: Expected number of results
            
        Returns:
            List of analysis dictionaries
        """
        try:
            # Extract JSON
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
            
            data = json.loads(response)
            
            if not isinstance(data, list):
                raise ValueError("Response is not a JSON array")
            
            results = []
            for item in data:
                suggestions = item.get('suggestions', [])
                prompt = item.get('clarification_prompt', '')
                
                # Validate
                try:
                    validated_suggestions = LLMResponseValidator.validate_suggestions(suggestions)
                except ValueError:
                    validated_suggestions = self._get_fallback_suggestions("")
                
                try:
                    validated_prompt = LLMResponseValidator.validate_clarification_prompt(prompt)
                except ValueError:
                    validated_prompt = "What specific criteria do you mean?"
                
                results.append({
                    'suggestions': validated_suggestions[:3],
                    'clarification_prompt': validated_prompt
                })
            
            # Ensure we have expected count
            while len(results) < expected_count:
                results.append({
                    'suggestions': self._get_fallback_suggestions(""),
                    'clarification_prompt': "What specific criteria do you mean?"
                })
            
            return results[:expected_count]
            
        except Exception as e:
            print(f"Error parsing batch suggestions: {e}")
            return [{
                'suggestions': self._get_fallback_suggestions(""),
                'clarification_prompt': "What specific criteria do you mean?"
            }] * expected_count
    
    def _fallback_individual_generate(self, 
                                     terms_data: List[Tuple[str, str, Optional[str]]]) -> List[Dict]:
        """
        Fallback to individual generation when batch fails.
        
        Args:
            terms_data: List of tuples (term, context, sentence)
            
        Returns:
            List of analysis dictionaries
        """
        results = []
        for term, context, sentence in terms_data:
            try:
                result = self.generate_complete_analysis(term, context, sentence)
                results.append(result)
            except Exception as e:
                print(f"Error generating suggestions for '{term}': {e}")
                results.append({
                    'suggestions': self._get_fallback_suggestions(term),
                    'clarification_prompt': f"What specific criteria do you mean by '{term}'?"
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

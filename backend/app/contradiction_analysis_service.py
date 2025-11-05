import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Type, Callable, Any
from pydantic import BaseModel, ValidationError
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .main import db
from .models import Requirement, ContradictionAnalysis, ConflictingPair
from .prompts import get_contradiction_analysis_prompt, get_json_correction_prompt # <-- IMPORTED CORRECTION PROMPT
from .schemas import ContradictionReportLLM


# ----------------------------------------------------------------------
# CONTRADICTION ANALYSIS SERVICE CLASS
# ----------------------------------------------------------------------

class ContradictionAnalysisService:
    """
    A service class responsible for orchestrating the LLM-based contradiction 
    analysis for project requirements.
    """
    def __init__(self, db_instance, user_id: Optional[str] = None, use_llm: bool = True):
        self.db = db_instance 
        self.user_id = user_id
        self.max_retries = 2 # Set max retries for LLM validation
        try:
            # Using GPT-4o for complex logic auditing
            self.llm_client = ChatOpenAI(model="gpt-4o", max_retries=5, temperature=0.1)
            self.llm_available = True
        except Exception as e:
            print(f"Warning: LLM initialization failed: {e}")
            self.llm_available = False

    def _fetch_requirements(self, document_id: int) -> List[Dict]:
        """
        Fetches the necessary data (ID, Type, Text) for all requirements linked 
        to a document from the database.
        """
        requirements = self.db.session.query(Requirement).filter(
            Requirement.source_document_id == document_id,
            Requirement.owner_id == self.user_id # Added ownership check for security
        ).all()
        
        # Structure the output to match the prompt's required input format
        return [{
            "id": req.req_id,
            "type": "UserStory" if req.description else "Requirement",
            "text": req.description or req.title
        } for req in requirements]

    # --- NEW: ROBUST LLM INVOCATION WITH RETRY ---
    def _invoke_llm_with_retry(
        self,
        initial_prompt: str,
        response_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Invokes the LLM, validates against the Pydantic model, and performs
        a correction loop if validation fails.
        """
        if not self.llm_available:
            raise Exception("LLM client is not available.")

        prompt = initial_prompt
        # This will hold the response string for the validation loop
        response_str = ""
        
        for attempt in range(self.max_retries + 1):
            try:
                print(f"LLM Contradiction Analysis: Attempt {attempt + 1}")
                
                # 1. Invoke the LLM with the current prompt
                chain = ChatPromptTemplate.from_template(prompt) | self.llm_client | StrOutputParser()
                response_str = chain.invoke({})
                
                # 2. Try to find JSON within markdown fences (common LLM failure)
                if "```json" in response_str:
                    response_str = response_str.split("```json")[1].split("```")[0].strip()
                elif "```" in response_str:
                    # Generic code block fence
                    response_str = response_str.split("```")[1].split("```")[0].strip()

                # 3. Validate the JSON string against the Pydantic model
                return response_model.model_validate_json(response_str)
            
            except ValidationError as e:
                print(f"Validation Error (Attempt {attempt + 1}): {e}")
                if attempt == self.max_retries:
                    # Max retries reached, fail and return empty model
                    # NOTE: Returning empty model ensures frontend doesn't crash on failure
                    return ContradictionReportLLM(contradictions=[])
                
                # Create a correction prompt
                prompt = get_json_correction_prompt(
                    bad_json=response_str,
                    validation_error=str(e)
                )
                # Next loop iteration will use this new correction prompt
                
            except Exception as e:
                print(f"LLM Invocation Error: {e}")
                # For non-validation errors (e.g., API timeout), fail gracefully
                return ContradictionReportLLM(contradictions=[])
        
        # Should be unreachable if max_retries works, but included as final fail-safe
        return ContradictionReportLLM(contradictions=[])


    def run_analysis(self, document_id: int, project_context: Optional[str] = None) -> ContradictionAnalysis:
        """
        Orchestrates the contradiction detection process using the LLM.
        """
        # 1. Fetch requirements for analysis
        requirements_data = self._fetch_requirements(document_id)
        
        if not requirements_data:
            # Ensure proper handling if no requirements exist
            raise ValueError("No requirements found for the specified document to analyze.")

        # 2. Build the LLM prompt
        initial_prompt = get_contradiction_analysis_prompt(
            requirements_json=requirements_data,
            project_context=project_context
        )
        
        # 3. Call LLM with correction loop (USING NEW ROBUST METHOD)
        validated_response = self._invoke_llm_with_retry(
            initial_prompt=initial_prompt,
            response_model=ContradictionReportLLM
        )

        # 4. Save analysis results to the database
        report = ContradictionAnalysis(
            source_document_id=document_id,
            owner_id=self.user_id,
            analyzed_at=datetime.utcnow(),
            total_conflicts_found=len(validated_response.contradictions),
            status='complete' if validated_response.contradictions else 'no_conflicts'
        )
        
        self.db.session.add(report)
        self.db.session.flush()

        for conflict_data in validated_response.contradictions:
            conflict = ConflictingPair(
                analysis_id=report.id,
                conflict_id=conflict_data.conflict_id,
                reason=conflict_data.reason,
                conflicting_requirement_ids=conflict_data.conflicting_requirement_ids,
                status='pending' 
            )
            self.db.session.add(conflict)
            
        self.db.session.commit()
        
        return report

    def get_latest_analysis(self, document_id: int) -> Optional[ContradictionAnalysis]:
        """
        Retrieves the most recent contradiction analysis for a given document.
        """
        return self.db.session.query(ContradictionAnalysis).filter(
            ContradictionAnalysis.source_document_id == document_id,
            ContradictionAnalysis.owner_id == self.user_id # Added ownership check
        ).order_by(ContradictionAnalysis.analyzed_at.desc()).first()
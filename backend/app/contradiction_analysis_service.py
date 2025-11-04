import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Type, Callable, Any
from pydantic import BaseModel, ValidationError
from langchain_openai import ChatOpenAI

from .main import db
from .models import Requirement, ContradictionAnalysis, ConflictingPair
from .prompts import get_contradiction_analysis_prompt
from .schemas import ContradictionReportLLM


# TODO: Pranav
# Move this to tests/ as a check
def validate_and_correct_llm_response(
    initial_prompt: str,
    response_model: Type[BaseModel],
    llm_client: ChatOpenAI,
    correction_prompt_builder: Callable,
    max_retries: int = 2
) -> BaseModel:
    """
    Mock utility to validate LLM response against a Pydantic model.
    In a real system, this contains the retry loop and error message feedback.
    """
    response_data = llm_client.invoke(initial_prompt, response_model)
    
    try:
        # Directly attempt to validate the mock response
        return response_model.model_validate(response_data)
    except ValidationError as e:
        print(f"MOCK VALIDATION ERROR: {e}")
        # In a real scenario, this would trigger the retry/correction logic
        return response_model(contradictions=[]) # Return empty result on mock failure

# ----------------------------------------------------------------------
# CONTRADICTION ANALYSIS SERVICE CLASS
# ----------------------------------------------------------------------

class ContradictionAnalysisService:
    """
    A service class responsible for orchestrating the LLM-based contradiction 
    analysis for project requirements.
    """
    def __init__(self, db_instance, user_id: Optional[str] = None, use_llm: bool = True):
        # db_instance is expected to be the Flask-SQLAlchemy instance (the 'db' object) as the service needs access to the session property (self.db.session).
        self.db = db_instance 
        self.user_id = user_id
        try:
            self.llm_client = ChatOpenAI(model="gpt-4o", temperature=0.1)
            self.llm_available = True
        except Exception as e:
            print(f"Warning: LLM initialization failed: {e}")
            print("Running in lexicon-only mode")
            self.llm_available = False

    def _fetch_requirements(self, document_id: int) -> List[Dict]:
        """
        Fetches the necessary data (ID, Type, Text) for all requirements linked 
        to a document from the database.
        """
        requirements = self.db.session.query(Requirement).filter(
            Requirement.source_document_id == document_id
        ).all()
        
        # Structure the output to match the prompt's required input format
        return [{
            "id": req.req_id,
            "type": "UserStory" if req.description else "Requirement",
            "text": req.description or req.title
        } for req in requirements]


    def run_analysis(self, document_id: int, project_context: Optional[str] = None) -> ContradictionAnalysis:
        """
        Orchestrates the contradiction detection process using the LLM.
        """
        # 1. Fetch requirements for analysis
        requirements_data = self._fetch_requirements(document_id)
        
        if not requirements_data:
            raise ValueError("No requirements found for the specified document to analyze.")

        # 2. Build the LLM prompt
        initial_prompt = get_contradiction_analysis_prompt(
            requirements_json=requirements_data,
            project_context=project_context
        )
        
        # 3. Call LLM with correction loop (via mock utility)
        validated_response_json = validate_and_correct_llm_response(
            initial_prompt=initial_prompt,
            response_model=ContradictionReportLLM,
            correction_prompt_builder=get_contradiction_analysis_prompt
        )

        # 4. Save analysis results to the database
        
        # Create the main analysis report
        report = ContradictionAnalysis(
            source_document_id=document_id,
            owner_id=self.user_id,
            analyzed_at=datetime.utcnow(),
            total_conflicts_found=len(validated_response_json.contradictions),
            status='complete' if validated_response_json.contradictions else 'no_conflicts'
        )
        
        self.db.session.add(report)
        self.db.session.flush() # Ensure the report ID is generated before adding conflicts

        # Create individual conflict records
        for conflict_data in validated_response_json.contradictions:
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
            ContradictionAnalysis.source_document_id == document_id
        ).order_by(ContradictionAnalysis.analyzed_at.desc()).first()

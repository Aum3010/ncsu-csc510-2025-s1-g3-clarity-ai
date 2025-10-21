from .main import db
from .models import Requirement
from .schemas import GeneratedRequirements

def save_requirements_to_db(validated_data: GeneratedRequirements, document_id: int):
    """
    Saves the validated Pydantic requirement objects to the database.
    """
    print(f"Saving {len(validated_data.epics)} epics to the database...")
    
    # Simple counter for unique req_id. In a real app, this would be more robust.
    req_counter = Requirement.query.count() + 1
    
    for epic in validated_data.epics:
        for user_story in epic.user_stories:
            new_req = Requirement(
                req_id=f"REQ-{req_counter:03d}",
                title=user_story.story,
                description="\n".join([f"- {ac}" for ac in user_story.acceptance_criteria]),
                status="Draft",
                priority="Medium", # Default value for now
                document_id=document_id
            )
            db.session.add(new_req)
            req_counter += 1
            
    db.session.commit()
    print("Successfully saved requirements to the database.")
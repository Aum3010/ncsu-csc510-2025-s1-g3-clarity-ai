from .main import db
from .models import Requirement, Tag # Import the Tag model
from .schemas import GeneratedRequirements

def save_requirements_to_db(validated_data: GeneratedRequirements, document_id: int):
    """
    Saves the validated requirements to the database, including finding or creating tags
    and linking them to the new requirements.
    """
    print(f"Saving {len(validated_data.epics)} epics to the database...")
    
    req_counter = Requirement.query.count() + 1
    
    for epic in validated_data.epics:
        for user_story in epic.user_stories:
            new_req = Requirement(
                req_id=f"REQ-{req_counter:03d}",
                title=user_story.story,
                description="\n".join([f"- {ac}" for ac in user_story.acceptance_criteria]),
                status="Draft", 
                priority=user_story.priority, 
                document_id=document_id
            )     
            for tag_name in user_story.suggested_tags:
                tag = Tag.query.filter_by(name=tag_name).first()
                
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                    db.session.flush() 
                
                new_req.tags.append(tag)
            db.session.add(new_req)
            req_counter += 1
            
    db.session.commit()
    print("Successfully saved requirements and their tags to the database.")
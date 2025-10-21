from pydantic import BaseModel, Field
from typing import List

class UserStory(BaseModel):
    """Defines the structure for a single user story and its criteria."""
    story: str = Field(
        ..., 
        description="The user story in the format 'As a [persona], I want [action], so that [benefit].'"
    )
    acceptance_criteria: List[str] = Field(
        ..., 
        description="A list of specific, testable acceptance criteria for the story."
    )

class Epic(BaseModel):
    """Groups a collection of related user stories under a single feature or epic."""
    epic_name: str = Field(..., description="The name of the feature or epic.")
    user_stories: List[UserStory]

class GeneratedRequirements(BaseModel):
    """The top-level JSON object that the LLM must return."""
    epics: List[Epic]
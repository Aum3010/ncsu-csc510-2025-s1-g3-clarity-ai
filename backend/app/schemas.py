from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class UserStory(BaseModel):
    """Defines the structure for a single, now classified, user story."""
    story: str = Field(..., description="The user story in the format 'As a...'")
    acceptance_criteria: List[str]
    # New fields for AI-powered classification
    priority: str = Field(..., description="The suggested priority: 'High', 'Medium', or 'Low'.")
    suggested_tags: List[str] = Field(..., description="A list of suggested tags for categorization.")

class Epic(BaseModel):
    """Groups a collection of related user stories under a single feature or epic."""
    epic_name: str = Field(..., description="The name of the feature or epic.")
    user_stories: List[UserStory]

class GeneratedRequirements(BaseModel):
    """The top-level JSON object that the LLM must return."""
    epics: List[Epic]

class ActionItem(BaseModel):
    task: str = Field(..., description="A single action item or task identified.")
    assignee: Optional[str] = Field(None, description="The person assigned, if mentioned (e.g., 'Dave', 'Maria').")

class MeetingSummary(BaseModel):
    summary: str = Field(..., description="A concise, high-level summary of the meeting discussion.")
    key_decisions: List[str] = Field(..., description="A list of final decisions made during the meeting.")
    open_questions: List[str] = Field(..., description="A list of topics that were left unresolved or require follow-up.")
    action_items: List[ActionItem]
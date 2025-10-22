from typing import Optional

def get_requirements_generation_prompt(
    context: str, 
    user_query: str, 
    error_message: Optional[str] = None
) -> str:
    """
    Generates a structured, role-based prompt for the LLM to create requirements.
    Optionally includes a corrective section if a previous attempt failed validation.
    """
    
    correction_section = ""
    if error_message:
        escaped_error = error_message.replace("{", "{{").replace("}", "}}")
        correction_section = f"""
        --- CORRECTION ---
        Your previous response failed validation with the following error:
        {escaped_error}
            
        Please analyze this error and correct your response to strictly adhere to the requested JSON schema. Do not apologize or add extra commentary.
        --- END CORRECTION ---
        """

    return f"""
    You are an expert Senior Product Manager and Software Architect, renowned for your ability to distill complex discussions into clear, actionable requirements. Your task is to analyze the provided context and generate a structured set of requirements.

    Analyze the following context carefully:
    --- CONTEXT ---
    {context}
    --- END CONTEXT ---

    Based on the context and the user's request, perform the following task:
    --- USER REQUEST ---
    {user_query}
    --- END USER REQUEST ---

    {correction_section}

    INSTRUCTIONS:
    1. Identify the main features or epics discussed in the context.
    2. For each epic, generate 3-5 clear, concise user stories in the format: "As a [persona], I want [action], so that [benefit]."
    3. For each user story, generate 2-4 specific, testable acceptance criteria.
    4. The final output MUST be a single, valid JSON object. Do not include any text, notes, or explanations outside of the JSON object.
    5. The JSON object must strictly adhere to the following schema:
        {{{{
          "epics": [
            {{{{
              "epic_name": "Name of the Epic/Feature",
              "user_stories": [
                {{{{
                  "story": "As a [persona], I want [action], so that [benefit].",
                  "acceptance_criteria": [
                    "Criteria 1",
                    "Criteria 2"
                  ]
                }}}}
              ]
            }}}}
          ]
        }}}}
    """


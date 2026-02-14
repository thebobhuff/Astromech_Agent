from langchain.tools import tool
import os
import sys

# Define the structure of a skill
OUTPUT_DIR = "app/skills"

@tool
def create_skill(name: str, description: str, instructions: str) -> str:
    """
    Creates a new skill for the agent.
    
    Args:
        name: The name of the skill (e.g., 'data-analysis').
        description: A short description of what the skill does and when to use it (triggers).
        instructions: The detailed markdown body explaining how to use the skill.
        
    Returns:
        Status message indicating success or failure.
    """
    try:
        if not name or not description or not instructions:
            return "Error: Name, description, and instructions are required."
            
        clean_name = name.lower().replace(" ", "-")
        skill_dir = os.path.join(OUTPUT_DIR, clean_name)
        
        if os.path.exists(skill_dir):
            return f"Error: Skill '{clean_name}' already exists."
        
        os.makedirs(skill_dir, exist_ok=True)
        
        # Construct SKILL.md content
        # We ensure the structure matches the Anthropic-like spec
        content = f"""---
name: {clean_name}
description: {description}
---

# {clean_name.replace("-", " ").title()}

{instructions}
"""
        
        file_path = os.path.join(skill_dir, "SKILL.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"Success: Skill '{clean_name}' created at {file_path}. It will be available in the next interaction."
        
    except Exception as e:
        return f"Error creating skill: {str(e)}"

def get_skill_tools():
    return [create_skill]

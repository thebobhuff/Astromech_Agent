import os
import glob
import frontmatter
from typing import List, Dict, Optional
from pydantic import BaseModel

class Skill(BaseModel):
    name: str
    description: str
    instructions: str
    metadata: Dict

def load_skills(skills_dir: str = "app/skills") -> List[Skill]:
    skills = []
    
    # Iterate over all directories in skills_dir
    if not os.path.exists(skills_dir):
        return []

    for item in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, item)
        if not os.path.isdir(skill_path) or item.startswith("__"):
            continue
            
        skill_file = os.path.join(skill_path, "SKILL.md")
        
        # Default/Fallback values
        name = item
        description = "No description available."
        instructions = ""
        metadata = {}

        if os.path.exists(skill_file):
            try:
                with open(skill_file, "r", encoding="utf-8") as f:
                    post = frontmatter.load(f)
                    
                metadata = post.metadata
                content = post.content
                
                # Extract basic info
                name = metadata.get("name", item)
                description = metadata.get("description", description)
                instructions = content
            except Exception as e:
                print(f"Error loading skill from {skill_file}: {e}")
                description = f"Error loading skill: {e}"
        else:
            description = "Uninitialized skill (Missing SKILL.md)"

        skills.append(Skill(
            name=name,
            description=description,
            instructions=instructions,
            metadata=metadata
        ))
            
    return skills

def format_skills_for_prompt(skills: List[Skill]) -> str:
    if not skills:
        return ""
        
    prompt_sections = ["## Available CLI Skills"]
    prompt_sections.append("You have access to the following specialized CLI tools. Use the 'terminal' tool to run them based on these instructions:")
    
    for skill in skills:
        prompt_sections.append(f"\n### {skill.name}")
        prompt_sections.append(f"{skill.description}")
        prompt_sections.append(f"Usage:\n{skill.instructions}")
        
    return "\n".join(prompt_sections)

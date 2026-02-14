from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import shutil
import frontmatter
from app.skills.loader import load_skills, Skill

router = APIRouter()

SKILLS_DIR = "app/skills"

class SkillCreate(BaseModel):
    name: str
    description: str
    instructions: str
    metadata: Optional[Dict] = {}

class SkillUpdate(BaseModel):
    description: Optional[str] = None
    instructions: Optional[str] = None
    metadata: Optional[Dict] = None

def get_skill_path(skill_slug: str) -> str:
    return os.path.join(SKILLS_DIR, skill_slug)

@router.get("/", response_model=List[Skill])
def get_skills():
    """List all available skills."""
    return load_skills(SKILLS_DIR)

@router.get("/{skill_slug}", response_model=Skill)
def get_skill(skill_slug: str = Path(..., title="The ID of the skill")):
    """Get details of a specific skill."""
    # Direct file access is better for single item
    skill_path = get_skill_path(skill_slug)
    skill_file = os.path.join(skill_path, "SKILL.md")
    
    if not os.path.exists(skill_path):
        raise HTTPException(status_code=404, detail="Skill directory not found")

    if not os.path.exists(skill_file):
        # Return placeholder for uninitialized skill
        return Skill(
            name=skill_slug,
            description="Uninitialized skill (Missing SKILL.md)",
            instructions="",
            metadata={}
        )

    try:
        with open(skill_file, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        
        return Skill(
            name=post.metadata.get("name", skill_slug),
            description=post.metadata.get("description", ""),
            instructions=post.content,
            metadata=post.metadata
        )
    except Exception as e:
        # Handle empty or corrupt file gracefully
        return Skill(
            name=skill_slug,
            description=f"Error loading skill: {str(e)}",
            instructions="",
            metadata={}
        )

@router.post("/", response_model=Skill)
def create_skill(skill: SkillCreate):
    """Create a new skill."""
    # Generate slug from name
    slug = skill.name.lower().replace(" ", "-")
    skill_path = get_skill_path(slug)
    
    if os.path.exists(skill_path):
         # Checking if SKILL.md exists to determine if it's truly a collision or just an uninitialized folder
         if os.path.exists(os.path.join(skill_path, "SKILL.md")):
            raise HTTPException(status_code=400, detail="Skill with this name already exists")
    else:
        os.makedirs(skill_path)
    
    file_path = os.path.join(skill_path, "SKILL.md")
    
    # Prepare Frontmatter
    post = frontmatter.Post(skill.instructions)
    post.metadata = skill.metadata or {}
    post.metadata["name"] = skill.name
    post.metadata["description"] = skill.description
    
    try:
        with open(file_path, "wb") as f:
            frontmatter.dump(post, f)
            
        return Skill(
            name=skill.name,
            description=skill.description,
            instructions=skill.instructions,
            metadata=post.metadata
        )
    except Exception as e:
        # Only cleanup if we just created the directory
        # shutil.rmtree(skill_path, ignore_errors=True) 
        raise HTTPException(status_code=500, detail=f"Failed to save skill: {e}")

@router.put("/{skill_slug}", response_model=Skill)
def update_skill(skill_update: SkillUpdate, skill_slug: str):
    """Update an existing skill."""
    skill_path = get_skill_path(skill_slug)
    file_path = os.path.join(skill_path, "SKILL.md")
    
    if not os.path.exists(skill_path):
        raise HTTPException(status_code=404, detail="Skill not found")
        
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
        else:
            # Create fresh if missing
            post = frontmatter.Post("")
            post.metadata["name"] = skill_slug
            
        if skill_update.description is not None:
            post.metadata["description"] = skill_update.description
        if skill_update.instructions is not None:
            post.content = skill_update.instructions
        if skill_update.metadata is not None:
            # Merge or replace? Let's merge standard fields and replace extra
            for k, v in skill_update.metadata.items():
                post.metadata[k] = v
                
        with open(file_path, "wb") as f:
            frontmatter.dump(post, f)
            
        return Skill(
            name=post.metadata.get("name", skill_slug),
            description=post.metadata.get("description", ""),
            instructions=post.content,
            metadata=post.metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update skill: {e}")

@router.delete("/{skill_slug}")
def delete_skill(skill_slug: str):
    """Delete a skill."""
    skill_path = get_skill_path(skill_slug)
    
    if not os.path.exists(skill_path):
        raise HTTPException(status_code=404, detail="Skill not found")
        
    try:
        shutil.rmtree(skill_path)
        return {"status": "success", "message": f"Skill {skill_slug} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete skill: {e}")

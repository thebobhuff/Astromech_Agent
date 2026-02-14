from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
from app.core.db import db
from app.core.scheduler import TaskQueue

router = APIRouter()
queue = TaskQueue()

class ProtocolTemplate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = ""
    default_priority: int = 3
    prompt_template: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class CreateProtocolRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    default_priority: int = 3
    prompt_template: str

class InstantiateProtocolRequest(BaseModel):
    template_id: str
    custom_title: Optional[str] = None
    priority_override: Optional[int] = None
    variables: Optional[dict] = None # For future expansion (variable substitution)

@router.get("/templates", response_model=List[ProtocolTemplate])
def list_templates():
    return db.get_templates()

@router.post("/templates", response_model=ProtocolTemplate)
def create_template(req: CreateProtocolRequest):
    new_template = ProtocolTemplate(
        name=req.name,
        description=req.description,
        default_priority=req.default_priority,
        prompt_template=req.prompt_template
    )
    db.add_template(new_template.model_dump())
    return new_template

@router.delete("/templates/{template_id}")
def delete_template(template_id: str):
    success = db.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"status": "success"}

@router.post("/instantiate")
def instantiate_protocol(req: InstantiateProtocolRequest):
    templates = db.get_templates()
    template = next((t for t in templates if t['id'] == req.template_id), None)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Use custom title if provided, else use Template Name
    title = req.custom_title or f"Protocol: {template['name']}"
    
    # Use overridden priority or default
    priority = req.priority_override if req.priority_override is not None else template['default_priority']
    
    # In a real SOP system, we might replace {{variables}} in the prompt_template here
    description = template['prompt_template']
    
    task = queue.add_task(
        title=title,
        description=description,
        priority=priority
    )
    
    return task

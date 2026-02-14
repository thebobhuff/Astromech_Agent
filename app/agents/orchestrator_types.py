from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.models import AgentSession


class EvaluatorOutput(BaseModel):
    intent: str = Field(description="Brief summary of what the user wants to do.")
    memory_queries: List[str] = Field(
        description="List of search queries to retrieve relevant context from memory."
    )


class RouterOutput(BaseModel):
    selected_tools: List[str] = Field(description="List of tool names to use for this task.")
    provider: str = Field(description="LLM provider to use (ollama, openai, anthropic).")
    model_name: str = Field(description="Specific model name to use.")
    reasoning: str = Field(description="Why this model and these tools were chosen.")


class PlanStep(BaseModel):
    id: str = Field(description="Stable short step id, e.g. 's1'")
    title: str = Field(description="Short action title")
    description: str = Field(description="What this step should do")
    depends_on: List[str] = Field(
        default_factory=list, description="Step IDs that must complete first"
    )
    parallelizable: bool = Field(
        default=False,
        description="True when this step can run in parallel with other ready steps",
    )
    priority: int = Field(default=3, description="1 (low) to 5 (urgent)")


class ExecutionPlan(BaseModel):
    name: str = Field(description="Short plan name")
    goal: str = Field(description="Overall goal this plan achieves")
    steps: List[PlanStep] = Field(default_factory=list)


class AgentResponse(BaseModel):
    response: str
    metadata: Dict[str, Any]
    session_data: Optional[AgentSession] = None

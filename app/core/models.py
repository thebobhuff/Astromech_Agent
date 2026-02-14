from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class MessageSchema(BaseModel):
    """Serializable format for LangChain messages using the OpenAI format (role, content, etc)"""
    role: str  # 'user', 'ai', 'system', 'tool'
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None  # Actual tool name for ToolMessages
    additional_kwargs: Dict[str, Any] = Field(default_factory=dict) # For provider-specific metadata (e.g. Gemini thought signatures)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Maximum messages kept in-memory per session.  Older messages beyond this
# limit are dropped from the in-memory list (they're already persisted to
# short-term memory summaries and to the JSON session file on disk).
MAX_SESSION_MESSAGES = 200


class AgentSession(BaseModel):
    """Full state of a conversation session"""
    session_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    messages: List[MessageSchema] = []
    context_files: List[str] = Field(default_factory=list, description="List of file paths currently in the active context window")
    metadata: Dict[str, Any] = {}
    last_summary_index: int = Field(default=0, description="Index of the last message that was summarized into short-term memory")

    def trim_messages(self):
        """Drop oldest messages beyond MAX_SESSION_MESSAGES to cap RAM usage.
        Adjusts last_summary_index accordingly."""
        overflow = len(self.messages) - MAX_SESSION_MESSAGES
        if overflow > 0:
            self.messages = self.messages[overflow:]
            self.last_summary_index = max(0, self.last_summary_index - overflow)

class AgentProfile(BaseModel):
    """Definition of an agent's capabilities and identity"""
    id: str
    name: str
    description: str
    system_prompt: str
    allowed_tools: List[str] = Field(default_factory=lambda: ["all"])
    parent_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


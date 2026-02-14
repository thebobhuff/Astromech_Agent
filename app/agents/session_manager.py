import os
import json
import logging
from datetime import datetime
from typing import Optional
from app.core.models import AgentSession, MessageSchema
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
import json as _json

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, storage_dir: str = "data/sessions"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, f"{session_id}.json")

    async def load_session(self, session_id: str) -> AgentSession:
        path = self._get_path(session_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return AgentSession(**data)
            except Exception as e:
                logger.error(f"Failed to load session {session_id}: {e}")
                # Fallback to new session if corrupted
        
        # Create new if not exists
        new_session = AgentSession(session_id=session_id)
        await self.save_session(new_session)
        return new_session

    async def save_session(self, session: AgentSession):
        session.updated_at = datetime.utcnow()
        # Trim before persisting to keep file sizes and memory bounded
        session.trim_messages()
        path = self._get_path(session.session_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session.model_dump(mode="json"), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")

    def dict_to_langchain(self, msg: MessageSchema) -> BaseMessage:
        """Convert stored Pydantic model to LangChain message object during runtime."""
        # Ensure content is never empty (Gemini rejects empty message text)
        content = msg.content if (msg.content and msg.content.strip()) else None

        if msg.role == "user":
            # Try to restore multimodal list content
            content_val = content
            if content and content.startswith('['):
                try:
                    content_val = _json.loads(content)
                except (_json.JSONDecodeError, Exception):
                    content_val = content
            return HumanMessage(content=content_val or "(continued)", additional_kwargs=msg.additional_kwargs)
        elif msg.role == "ai":
            tc = msg.tool_calls or []
            if tc and not content:
                return AIMessage(content="(calling tools)", tool_calls=tc, additional_kwargs=msg.additional_kwargs)
            # Filter out stored placeholder text that the LLM might parrot
            if content and content.strip('() ').lower() in ('empty response', 'empty'):
                content = None
            return AIMessage(content=content or "[no response was generated]", tool_calls=tc, additional_kwargs=msg.additional_kwargs)
        elif msg.role == "system":
            return SystemMessage(content=content or "(system)", additional_kwargs=msg.additional_kwargs)
        elif msg.role == "tool":
            return ToolMessage(content=content or "(empty result)", tool_call_id=msg.tool_call_id, name=msg.tool_name or "tool", additional_kwargs=msg.additional_kwargs)
        return HumanMessage(content=content or "(continued)", additional_kwargs=msg.additional_kwargs) # Fallback

    def langchain_to_dict(self, msg: BaseMessage) -> MessageSchema:
        """Convert LangChain message to Pydantic model for storage."""
        role = "user"
        tool_calls = None
        tool_call_id = None
        tool_name = None

        # Serialize content: preserve list content (multimodal) via JSON
        raw_content = msg.content
        if isinstance(raw_content, list):
            content = _json.dumps(raw_content)
        else:
            content = str(raw_content) if raw_content else ""

        if isinstance(msg, HumanMessage):
             role = "user"
        elif isinstance(msg, AIMessage):
             role = "ai"
             tool_calls = msg.tool_calls
        elif isinstance(msg, SystemMessage):
             role = "system"
        elif isinstance(msg, ToolMessage):
             role = "tool"
             tool_call_id = msg.tool_call_id
             tool_name = getattr(msg, 'name', None)

        return MessageSchema(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            additional_kwargs=msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {},
        )

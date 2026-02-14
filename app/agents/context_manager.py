import os
from typing import List, Optional, Dict, Tuple
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, ToolMessage, HumanMessage

# Maximum number of recent messages to send to the LLM
MAX_MESSAGE_WINDOW = 10
# Number of new messages between auto-summarizations
SUMMARY_INTERVAL = 10

# Patterns that indicate a failed/placeholder AI response that should be stripped from history
_DEAD_RESPONSE_PATTERNS = frozenset([
    '(empty response)',
    '[no response was generated]',
    '(empty)',
    '(thinking)',
    "I processed your request but wasn't able to generate a response. Please try rephrasing or starting a new session.",
    "I processed your request but wasn't able to formulate a response.",
    "I apologize, but I encountered an unexpected issue and could not generate a response. Please try again.",
    "I wasn't able to generate a response. Please try again or rephrase your request.",
    "Max execution turns (5) reached. I was unable to generate a summary. Please try again or rephrase your request.",
    "Max execution turns (5) reached without final answer and summary failed.",
    "Max execution turns (15) reached. I was unable to generate a summary. Please try again or rephrase your request.",
    "Max execution turns (30) reached. I was unable to generate a summary. Please try again or rephrase your request.",
])

# Partial patterns that indicate a non-actionable AI response (model described
# what it *would* do instead of actually invoking tools).  Checked with
# case-insensitive substring match.
_DEAD_RESPONSE_SUBSTRINGS = (
    "i need your permission",
    "i would need",
    "i will need your",
    "i need to confirm",
    "to proceed, i need",
    "to do this, i need",
    "to ensure i can access",
    "i am ready to check",
    "i'm ready to check",
    "please provide",
    "i'll need your",
    "Error communicating with",
    "encountered a system error",
)


def _is_dead_response(content: str) -> bool:
    """Check if an AI message is a placeholder/failure that should be excluded from history.
    
    Matches exact patterns AND partial substring patterns to catch LLM responses
    that describe intended actions instead of performing them (feedback-loop poison).
    """
    if not content:
        return True
    stripped = content.strip()
    if not stripped:
        return True
    lower = stripped.lower()
    # Exact match
    if lower in {p.lower() for p in _DEAD_RESPONSE_PATTERNS}:
        return True
    # Substring match — catch "I would need your permission" style responses
    # Only flag short responses (< 400 chars) to avoid false positives on
    # long, substantive replies that happen to contain a trigger phrase.
    if len(stripped) < 400:
        for sub in _DEAD_RESPONSE_SUBSTRINGS:
            if sub in lower:
                return True
    return False


class ContextManager:
    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        # Cache file->rendered context blocks to avoid repeated disk reads.
        # key: absolute file path
        # value: ((mtime, size), rendered_block)
        self._context_file_cache: Dict[str, Tuple[Tuple[float, int], str]] = {}

    def _estimate_tokens(self, text: str) -> int:
        """Approximate token count (Char / 4) to avoid heavy dependencies like encoding libraries."""
        if not text:
            return 0
        return len(text) // 4

    def _read_context_files(self, files: List[str]) -> str:
        """Reads content of specified files to include in context."""
        if not files:
            return ""
        
        content_parts = ["\n\n--- ACTIVE CONTEXT FILES ---"]
        binary_extensions = {
            '.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff',
            '.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac',
            '.mp4', '.avi', '.mov', '.mkv', '.webm',
            '.pdf', '.zip', '.tar', '.gz', '.7z', '.rar',
            '.exe', '.dll', '.bin', '.iso'
        }

        for file_path in files:
            try:
                abs_path = os.path.abspath(file_path)
                if os.path.exists(abs_path):
                    ext = os.path.splitext(abs_path)[1].lower()
                    if ext in binary_extensions:
                        content_parts.append(f'<file path="{file_path}">\n[BINARY/MEDIA FILE - CONTENT OMITTED. USE TOOLS TO PROCESS THIS FILE.]\n</file>')
                        continue

                    stat = os.stat(abs_path)
                    cache_version = (stat.st_mtime, stat.st_size)
                    cached = self._context_file_cache.get(abs_path)
                    if cached and cached[0] == cache_version:
                        content_parts.append(cached[1])
                        continue

                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_content = f.read()
                        # Limit individual file size to avoid blowing up context purely on one file
                        # 20k chars is approx 5k tokens.
                        if len(file_content) > 20000:
                            file_content = file_content[:20000] + "\n... [TRUNCATED - FILE TOO LARGE]"
                        rendered = f'<file path="{file_path}">\n{file_content}\n</file>'
                        self._context_file_cache[abs_path] = (cache_version, rendered)
                        content_parts.append(rendered)
                else:
                    self._context_file_cache.pop(abs_path, None)
                    content_parts.append(f'<file path="{file_path}">\n[FILE NOT FOUND]\n</file>')
            except Exception as e:
                self._context_file_cache.pop(os.path.abspath(file_path), None)
                content_parts.append(f'<file path="{file_path}">\n[ERROR READING FILE: {e}]\n</file>')
        
        return "\n".join(content_parts)

    def _group_messages(self, history: List[BaseMessage]) -> List[List[BaseMessage]]:
        """
        Groups messages into atomic units that must stay together.
        A tool-call group = [AIMessage(tool_calls), ToolMessage, ..., ToolMessage].
        Standalone messages are wrapped as single-element lists.
        """
        groups: List[List[BaseMessage]] = []
        i = 0
        while i < len(history):
            msg = history[i]
            # Start of a tool-call group
            if isinstance(msg, AIMessage) and getattr(msg, 'tool_calls', None):
                group = [msg]
                j = i + 1
                while j < len(history) and isinstance(history[j], ToolMessage):
                    group.append(history[j])
                    j += 1
                groups.append(group)
                i = j
            else:
                groups.append([msg])
                i += 1
        return groups

    def sanitize_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Ensures message list satisfies Gemini turn-ordering rules:
        - First non-system message must be HumanMessage.
        - AIMessage with tool_calls must be followed only by ToolMessages.
        - No orphaned ToolMessages without a preceding AIMessage(tool_calls).
        - No consecutive AIMessages (merge content if needed).
        """
        if not messages:
            return messages

        result: List[BaseMessage] = []

        # Separate leading system messages
        idx = 0
        while idx < len(messages) and isinstance(messages[idx], SystemMessage):
            # Ensure system messages have content
            if messages[idx].content and str(messages[idx].content).strip():
                result.append(messages[idx])
            else:
                result.append(SystemMessage(content="(system)"))
            idx += 1

        body = messages[idx:]
        sanitized: List[BaseMessage] = []

        i = 0
        while i < len(body):
            msg = body[i]

            if isinstance(msg, ToolMessage):
                # Orphaned ToolMessage — check if previous was an AI with tool_calls
                if sanitized and isinstance(sanitized[-1], AIMessage) and getattr(sanitized[-1], 'tool_calls', None):
                    sanitized.append(msg)
                else:
                    # Drop orphaned ToolMessage
                    i += 1
                    continue

            elif isinstance(msg, AIMessage):
                if getattr(msg, 'tool_calls', None):
                    # AI with tool calls — verify subsequent ToolMessages exist
                    tool_call_ids = {tc.get('id') or tc.get('tool_call_id') for tc in msg.tool_calls}
                    tool_msgs = []
                    j = i + 1
                    while j < len(body) and isinstance(body[j], ToolMessage):
                        # Ensure ToolMessage has non-empty content (Gemini requires it)
                        tm = body[j]
                        if not tm.content or not str(tm.content).strip():
                            tool_msgs.append(ToolMessage(content="(empty result)", tool_call_id=tm.tool_call_id, name=getattr(tm, 'name', 'tool')))
                        else:
                            tool_msgs.append(tm)
                        j += 1
                    if tool_msgs:
                        # Ensure the AI message itself has non-empty content (Gemini requires it)
                        if not msg.content or not str(msg.content).strip():
                            patched_msg = AIMessage(content="(calling tools)", tool_calls=msg.tool_calls)
                        else:
                            patched_msg = msg
                        sanitized.append(patched_msg)
                        sanitized.extend(tool_msgs)
                        i = j
                        continue
                    else:
                        # AI tool_calls with no matching ToolMessages — drop the tool_calls
                        sanitized.append(AIMessage(content=msg.content or "(tool call attempted)"))
                else:
                    # Plain AI message — avoid consecutive AI messages
                    # Ensure non-empty content
                    ai_content = msg.content if (msg.content and str(msg.content).strip()) else "(empty response)"
                    if sanitized and isinstance(sanitized[-1], AIMessage) and not getattr(sanitized[-1], 'tool_calls', None):
                        # Merge into previous
                        prev = sanitized[-1]
                        prev_content = prev.content if isinstance(prev.content, str) else str(prev.content)
                        new_content = ai_content if isinstance(ai_content, str) else str(ai_content)
                        sanitized[-1] = AIMessage(content=prev_content + "\n" + new_content)
                    else:
                        sanitized.append(AIMessage(content=ai_content))
            else:
                # HumanMessage or others — just append
                sanitized.append(msg)

            i += 1

        # Ensure first non-system message is a HumanMessage
        if sanitized and not isinstance(sanitized[0], HumanMessage):
            sanitized.insert(0, HumanMessage(content="(continued conversation)"))

        # Final pass: ensure ALL messages have non-empty content (Gemini requirement)
        final = []
        for m in result + sanitized:
            content = m.content
            if not content or (isinstance(content, str) and not content.strip()):
                if isinstance(m, HumanMessage):
                    final.append(HumanMessage(content="(continued)"))
                elif isinstance(m, AIMessage):
                    if getattr(m, 'tool_calls', None):
                        final.append(AIMessage(content="(calling tools)", tool_calls=m.tool_calls))
                    else:
                        final.append(AIMessage(content="[processing]"))
                elif isinstance(m, SystemMessage):
                    final.append(SystemMessage(content="(system)"))
                elif isinstance(m, ToolMessage):
                    final.append(ToolMessage(content="(empty result)", tool_call_id=m.tool_call_id, name=getattr(m, 'name', 'tool')))
                else:
                    final.append(m)
            else:
                final.append(m)
        return final

    def optimize_context(self, system_prompt: str, history: List[BaseMessage], new_prompt: str, context_files: Optional[List[str]] = None, short_term_context: str = "") -> List[BaseMessage]:
        """
        Returns a list of messages that fits within a sliding window.
        
        Strategy:
        1. System prompt + short-term memory summaries + context files = SystemMessage
        2. Only the last MAX_MESSAGE_WINDOW messages from history are included.
        3. Tool-call groups are kept intact (never split AI+ToolMessages).
        4. Final sanitization ensures valid turn ordering for Gemini.
        """
        
        # 1. Prepare File Context
        file_context_str = self._read_context_files(context_files) if context_files else ""
        
        # 2. Build full system prompt with short-term memory
        parts = [system_prompt]
        if short_term_context:
            parts.append(short_term_context)
        if file_context_str:
            parts.append(file_context_str)
        full_system_prompt = "\n\n".join(parts)
        
        # 3. Filter out dead/failed responses from history before windowing
        #    This prevents poisoned sessions where repeated failures create a feedback loop
        cleaned_history: List[BaseMessage] = []
        i = 0
        while i < len(history):
            msg = history[i]
            if isinstance(msg, AIMessage) and not getattr(msg, 'tool_calls', None):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                if _is_dead_response(content):
                    # Skip this dead AI message.
                    # Also skip the preceding HumanMessage if it exists (it was the prompt that got no real answer)
                    if cleaned_history and isinstance(cleaned_history[-1], HumanMessage):
                        cleaned_history.pop()
                    i += 1
                    continue
            cleaned_history.append(msg)
            i += 1
        
        # 4. Select last N messages using atomic grouping + token budget
        groups = self._group_messages(cleaned_history)
        
        # Reserve ~30% of context for system prompt + new prompt + LLM response
        system_tokens = self._estimate_tokens(full_system_prompt)
        prompt_tokens = self._estimate_tokens(new_prompt)
        reserved = system_tokens + prompt_tokens + 4000  # 4k for LLM response
        token_budget = max(self.max_tokens - reserved, 8000)
        
        selected_groups: List[List[BaseMessage]] = []
        group_count = 0
        used_tokens = 0
        
        for group in reversed(groups):
            # Estimate tokens for this group
            group_tokens = sum(
                self._estimate_tokens(m.content if isinstance(m.content, str) else str(m.content))
                for m in group
            )
            # Stop if adding this group would bust the budget OR exceed MAX_MESSAGE_WINDOW
            if used_tokens + group_tokens > token_budget and selected_groups:
                break
            selected_groups.insert(0, group)
            used_tokens += group_tokens
            group_count += 1
            if group_count >= MAX_MESSAGE_WINDOW:
                break
        
        # Flatten groups back to message list
        selected_history = [msg for group in selected_groups for msg in group]
        
        # 4. Sanitize for valid turn ordering
        all_msgs = [SystemMessage(content=full_system_prompt)] + selected_history
        return self.sanitize_messages(all_msgs)

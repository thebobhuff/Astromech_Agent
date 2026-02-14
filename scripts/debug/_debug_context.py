"""Debug: simulate what the LLM actually receives."""
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.agents.session_manager import SessionManager
from app.agents.context_manager import ContextManager
from app.memory.short_term import ShortTermMemoryManager

async def main():
    sm = SessionManager()
    cm = ContextManager()
    stm = ShortTermMemoryManager()
    
    session = await sm.load_session("telegram_5112368377")
    print(f"Session has {len(session.messages)} messages")
    print(f"last_summary_index: {session.last_summary_index}")
    
    # Convert to langchain messages (exactly as orchestrator does)
    history_msgs = [sm.dict_to_langchain(m) for m in session.messages]
    
    # Show what the sliding window produces
    short_term_ctx = stm.get_today_context(session.session_id)
    print(f"\nShort-term context length: {len(short_term_ctx)} chars")
    if short_term_ctx:
        print(f"Short-term preview: {short_term_ctx[:200]}...")
    
    # Simulate optimize_context
    messages = cm.optimize_context(
        "SYSTEM PROMPT (truncated for debug)",
        history_msgs,
        "Test",
        session.context_files,
        short_term_context=short_term_ctx
    )
    
    print(f"\nOptimized messages count: {len(messages)}")
    for i, m in enumerate(messages):
        role = type(m).__name__
        content = str(m.content)[:150].replace("\n", "\\n")
        tc = len(getattr(m, 'tool_calls', []) or [])
        extra = f" [tool_calls={tc}]" if tc else ""
        print(f"  [{i}] {role}: {repr(content)}{extra}")

asyncio.run(main())

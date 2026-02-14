import asyncio
import sys
import os
from pathlib import Path

# Ensure app modules can be found
repo_root = Path(__file__).resolve().parents[2]
sys.path.append(str(repo_root))

from app.agents.orchestrator import AgentOrchestrator
from app.core.models import AgentSession
import uuid

async def test_sub_agent_system():
    print(">>> Testing Sub-Agent System <<<")
    
    # 1. Initialize Main Orchestrator (No specific profile, full access)
    main_orchestrator = AgentOrchestrator()
    session = AgentSession(session_id="test-session-" + str(uuid.uuid4()))
    
    # 2. Craft a prompt that requires delegation
    # We ask the main agent to ask the 'researcher' about something.
    prompt = "Use the 'delegate_task' tool to ask the 'researcher' agent to explain what 'Agentic Workflow' means in one sentence."
    
    print(f"User Prompt: {prompt}")
    print("-" * 50)
    
    # 3. Run
    # This should trigger:
    # Main Agent -> Decides to use delegate_task -> Spawns Researcher -> Researcher runs -> Returns text -> Main Agent reports back
    response = await main_orchestrator.run(prompt, session)
    
    print("-" * 50)
    print(f"Final Response:\n{response.response}")
    print("-" * 50)
    
    # 4. Verify Metadata
    tools_used = response.metadata.get("tools_used", [])
    print(f"Tools Used: {tools_used}")
    
    if "delegate_task" in tools_used:
        print("SUCCESS: Main agent used 'delegate_task'.")
    else:
        print("WARNING: Main agent did NOT use 'delegate_task'. It might have answered directly.")

if __name__ == "__main__":
    if os.name == 'nt':
        os.system('color')
    asyncio.run(test_sub_agent_system())

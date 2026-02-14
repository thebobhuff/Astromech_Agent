print("Importing FastAPI...")
from fastapi import FastAPI
print("Importing Pydantic...")
from pydantic import BaseModel
print("Importing Orchestrator...")
try:
    from app.agents.orchestrator import AgentOrchestrator
    print("Orchestrator Imported.")
except Exception as e:
    print(f"Orchestrator Failed: {e}")
    import traceback
    traceback.print_exc()

print("Done.")
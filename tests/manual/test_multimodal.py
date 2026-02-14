from app.agents.orchestrator import AgentOrchestrator
from app.core.config import settings
import asyncio

async def test_multimodal():
    orchestrator = AgentOrchestrator()
    print("Testing multimodal capabilities...")
    
    # Assuming there's an image file for testing, but I'll skip actual file reading for this mock test
    # and just verify the parameter passing doesn't crash functionality.
    
    response = await orchestrator.run("Describe this image (mock test)", images=["https://placehold.co/600x400/png"])
    print(response.response)

if __name__ == "__main__":
    if settings.OPENAI_API_KEY or settings.GOOGLE_API_KEY:
        asyncio.run(test_multimodal())
    else:
        print("No API keys found, skipping actual request.")

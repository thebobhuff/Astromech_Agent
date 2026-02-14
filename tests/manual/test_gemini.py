import asyncio
from app.core.config import settings
from app.core.llm import get_llm
from langchain_core.messages import HumanMessage

async def main():
    print(f"Testing Gemini Integration...")
    print(f"Provider: {settings.DEFAULT_LLM_PROVIDER}")
    print(f"Key configured: {'Yes' if settings.GOOGLE_API_KEY else 'No'}")

    if not settings.GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY is missing in .env")
        return

    try:
        # Force provider to gemini to test it specifically, or use default if it is gemini
        llm = get_llm(provider="gemini", model_name="gemini-2.0-flash")
        
        print("\nSending request to Gemini...")
        msg = HumanMessage(content="Hello! Are you working correctly? Reply with 'Gemini Online'.")
        response = await llm.ainvoke([msg])
        
        print(f"\nResponse:\n{response.content}")
        print("\nSUCCESS: Gemini API is reachable from this terminal.")
        
    except Exception as e:
        print(f"\nFAILURE: {e}")

if __name__ == "__main__":
    asyncio.run(main())

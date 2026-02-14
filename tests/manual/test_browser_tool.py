import asyncio
from app.tools.browser import browse_url

async def main():
    print("Testing Browse URL...")
    # Using a simple, reliable URL
    url = "https://example.com"
    
    print(f"Visiting {url}...")
    result = await browse_url.ainvoke({"url": url})
    
    print("--- Result ---")
    print(result[:500]) # First 500 chars
    
    if "Example Domain" in result:
        print("\nSUCCESS: Found expected content.")
    else:
        print(f"\nFAILURE: Unexpected content: {result[:100]}")

if __name__ == "__main__":
    asyncio.run(main())

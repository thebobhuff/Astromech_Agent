import asyncio
from app.tools.browser import browse_url

async def main():
    print("Testing browse_url...")
    try:
        result = await browse_url.ainvoke("https://example.com")
        print("RESULT:")
        print(result)
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())

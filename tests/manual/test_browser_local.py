import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_browser():
    try:
        from app.core.browser_launcher import browser_launcher
        
        print("Launching Browser...")
        cdp_url = browser_launcher.launch(headless=False)
        print(f"Browser launched at {cdp_url}")
        
        from playwright.async_api import async_playwright
        
        print("Connecting with Playwright...")
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            print("Connected!")
            
            context = browser.contexts[0]
            page = await context.new_page()
            await page.goto("https://example.com")
            print("Navigated to example.com")
            await page.screenshot(path="test_browser.png")
            print("Screenshot taken")
            await page.close()
            # We don't close browser here to keep it persistent
            
        print("Test Complete. Browser should still be open.")
        
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_browser())

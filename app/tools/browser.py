from langchain.tools import tool
import asyncio
from typing import Optional
from app.core.browser_launcher import browser_launcher
import logging

logger = logging.getLogger(__name__)

@tool
async def browse_url(url: str) -> str:
    """
    Visits a URL using a Local OS Browser (via Chrome DevTools Protocol) to render JavaScript and extract content.
    This uses a persistent browser instance, so cookies and sessions may be preserved.
    """
    try:
        from playwright.async_api import async_playwright
        from bs4 import BeautifulSoup
    except ImportError:
         return "Error: Playwright is not installed. Please install 'playwright' and 'beautifulsoup4'."

    try:
        # Ensure the browser is running
        cdp_url = browser_launcher.launch(headless=False) # Make sure it's visible as requested ("like its local")
        
        async with async_playwright() as p:
            # Connect to the running browser
            try:
                browser = await p.chromium.connect_over_cdp(cdp_url)
            except Exception as e:
                return f"Error connecting to browser: {e}. Is Chrome running?"

            # Use the default context if available, or create a new page
            # Note: connect_over_cdp usually gives access to the existing browser context
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            
            page = await context.new_page()
            
            # Timeout 30s
            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                await page.close() # Close just the tab
                return f"Error navigating to {url}: {e}"
            
            # Get content
            content = await page.content()
            
            # Cleanup - Close the tab, but keep the browser running
            await page.close()
            # Do NOT await browser.close() as it terminates the connection/process depending on how it was launched
            # For connect_over_cdp, browser.close() disconnects. It usually doesn't kill the browser unless connected differently.
            # But let's be safe and just disconnect.
            
            # Parse
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove clutter
            for tag in soup(["script", "style", "nav", "footer", "iframe", "svg", "noscript"]):
                tag.decompose()
                
            text = soup.get_text(separator="\n", strip=True)
            
            if len(text) > 20000:
                return text[:20000] + "\n... [TRUNCATED]"
            return text
            
    except Exception as e:
        logger.error(f"Browse Error: {e}", exc_info=True)
        return f"Error browsing {url}: {str(e)}"

def get_browser_tools():
    return [browse_url]

from langchain.tools import tool
import asyncio
from typing import Optional

# We need to handle the import carefully so it doesn't crash if playwright isn't installed
try:
    from playwright.async_api import async_playwright
    from bs4 import BeautifulSoup
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

@tool
async def browse_url(url: str) -> str:
    """
    Visits a URL using a Headless Browser (Playwright) to render JavaScript and extract content.
    Use this for reading documentation, news sites, or pages where 'visit_webpage' fails.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return "Error: Playwright is not installed. Please install 'playwright' and 'beautifulsoup4'."

    try:
        async with async_playwright() as p:
            # Launch configs suitable for server/sandbox
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"] 
            )
            # Create a context (like an incognito window)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Timeout 30s
            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                await browser.close()
                return f"Error navigating to {url}: {e}"
            
            # Get content
            content = await page.content()
            
            # Parse
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove clutter
            for tag in soup(["script", "style", "nav", "footer", "iframe", "svg", "noscript"]):
                tag.decompose()
                
            text = soup.get_text(separator="\n", strip=True)
            
            await browser.close()
            
            if len(text) > 20000:
                return text[:20000] + "\n... [TRUNCATED]"
            return text
            
    except Exception as e:
        return f"Error browsing {url}: {str(e)}"

def get_browser_tools():
    return [browse_url]

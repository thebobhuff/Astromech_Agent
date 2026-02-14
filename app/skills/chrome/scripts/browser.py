import argparse
import sys
import asyncio
from playwright.async_api import async_playwright
import markdownify

async def browse(url, action="read", output_path=None):
    async with async_playwright() as p:
        # Launch browser (headless by default)
        browser = await p.chromium.launch(headless=True)
        # Create context with user agent to avoid bot detection
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"Navigating to {url}...")
            await page.goto(url, timeout=30000, wait_until="networkidle")
            
            if action == "read":
                content = await page.content()
                # Convert to markdown for better LLM consumption
                text = markdownify.markdownify(content, heading_style="ATX")
                # Strip excessive newlines
                text = "\n".join([line for line in text.splitlines() if line.strip()])
                print(text)
                
            elif action == "screenshot":
                if not output_path:
                    output_path = "screenshot.png"
                await page.screenshot(path=output_path, full_page=True)
                print(f"Screenshot saved to {output_path}")
                
            elif action == "text":
                content = await page.inner_text("body")
                print(content)
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

def main():
    parser = argparse.ArgumentParser(description="Headless Chrome Browser Tool")
    parser.add_argument("url", help="URL to visit")
    parser.add_argument("--action", choices=["read", "screenshot", "text"], default="read", help="Action to perform")
    parser.add_argument("--output", help="Output path for screenshots")
    
    args = parser.parse_args()
    
    if not args.url.startswith("http"):
        args.url = "https://" + args.url
        
    asyncio.run(browse(args.url, args.action, args.output))

if __name__ == "__main__":
    main()

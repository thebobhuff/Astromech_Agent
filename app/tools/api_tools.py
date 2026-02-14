from langchain.tools import tool
import requests
import os
import json
from markdownify import markdownify as md

@tool
def ingest_api_doc(url: str, output_path: str) -> str:
    """
    Fetches API documentation from a URL and saves it as Markdown or JSON locally.
    Use this to 'ingest' knowledge into a skill's 'references' directory.
    
    Args:
        url: The URL to fetch (HTML documentation or JSON/YAML spec).
        output_path: The local path to save the file (e.g., 'app/skills/my-skill/references/notes.md').
    """
    try:
        # Create dir if not exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        content_type = response.headers.get("Content-Type", "").lower()
        content = ""
        
        if "json" in content_type or url.endswith(".json"):
            # Pretty print JSON
            try:
                data = response.json()
                content = json.dumps(data, indent=2)
            except:
                content = response.text
        elif "html" in content_type:
            # Convert HTML to Markdown
            content = md(response.text, heading_style="ATX")
        else:
            # Fallback for text/yaml
            content = response.text
            
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"Success: Ingested {len(content)} characters from {url} to {output_path}."
        
    except Exception as e:
        return f"Error ingesting API doc: {str(e)}"

# Export list of tools
def get_api_tools():
    return [ingest_api_doc]

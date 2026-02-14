from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from app.core.config import settings

# Try importing Search components and configure provider
search_tool = None
SEARCH_AVAILABLE = False
SEARCH_PROVIDER = "None"

try:
    if settings.BRAVE_SEARCH_API_KEY:
        from langchain_community.tools import BraveSearch
        search_tool = BraveSearch.from_api_key(api_key=settings.BRAVE_SEARCH_API_KEY, search_kwargs={"count": 5})
        SEARCH_AVAILABLE = True
        SEARCH_PROVIDER = "Brave"
    else:
        try:
            from duckduckgo_search import DDGS
            
            class LocalDDGSearch:
                def run(self, query: str) -> str:
                    with DDGS() as ddgs:
                        # 'timelimit="y"' is equivalent to time="y" in older versions, checking param names is safer
                        # but "text" method usually takes keywords. 
                        # We'll use defaults to be safe or minimal params.
                        results = list(ddgs.text(query, max_results=5))
                    
                    if not results:
                        return "No results found."
                    
                    # Format results clearly
                    formatted = []
                    for r in results:
                        title = r.get('title', 'No Title')
                        link = r.get('href', r.get('url', ''))
                        snippet = r.get('body', r.get('snippet', ''))
                        formatted.append(f"Title: {title}\nLink: {link}\nSnippet: {snippet}")
                        
                    return "\n---\n".join(formatted)

            search_tool = LocalDDGSearch()
            SEARCH_AVAILABLE = True
            SEARCH_PROVIDER = "DuckDuckGo"
            
        except ImportError:
            # Fallback to attempting langchain import if local import fails
            # This covers cases where only the legacy package is installed
            from langchain_community.tools import DuckDuckGoSearchResults
            from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
            
            # Initialize DDG Wrapper
            wrapper = DuckDuckGoSearchAPIWrapper(max_results=5, time="y") # Past year results mainly
            search_tool = DuckDuckGoSearchResults(api_wrapper=wrapper, backend="api")
            SEARCH_AVAILABLE = True
            SEARCH_PROVIDER = "DuckDuckGo"
        
except (ImportError, Exception) as e:
    print(f"Warning: Web Search disabled. Error: {e}")
    SEARCH_AVAILABLE = False
    search_tool = None

@tool
def web_search(query: str) -> str:
    """
    Performs a web search using DuckDuckGo to find information, news, or documentation.
    Use this tool when you need information that is not in your local memory.
    Returns a list of search results with titles, snippets, and links.
    """
    if not SEARCH_AVAILABLE or not search_tool:
        return "Web search is currently unavailable due to missing dependencies."
        
    try:
        return search_tool.run(query)
    except Exception as e:
        return f"Error performing search: {str(e)}"

@tool
def visit_webpage(url: str) -> str:
    """
    Visits a specific URL and returns the main text content.
    Use this to read documentation, articles, or github repositories found via search.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Smart extraction: remove script/style
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
            
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Truncate if too long (approx 2000 words / 8000 chars) to fit in context
        return text[:8000] + ("...\n[Content Truncated]" if len(text) > 8000 else "")
        
    except Exception as e:
        return f"Error visiting webpage: {str(e)}"

def get_web_tools():
    return [web_search, visit_webpage]

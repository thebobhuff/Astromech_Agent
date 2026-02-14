print("1")
from langchain_community.chat_models import ChatOllama
print("2")
from langchain_google_genai import ChatGoogleGenerativeAI
print("3")
from app.memory.rag import VectorMemory
print("4")
from app.tools.web_search import get_web_tools
print("5")
print("All Imports OK")
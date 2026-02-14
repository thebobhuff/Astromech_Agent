print("Checking openai...")
try:
    from langchain_openai import ChatOpenAI
    print("OpenAI OK")
except Exception as e:
    print(f"OpenAI Failed: {e}")

print("Checking google...")
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    print("Google OK")
except Exception as e:
    print(f"Google Failed: {e}")

print("Checking ollama...")
try:
    from langchain_community.chat_models import ChatOllama
    print("Ollama OK")
except Exception as e:
    print(f"Ollama Failed: {e}")

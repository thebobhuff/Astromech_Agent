from langchain.tools import tool
import os
import mimetypes
import logging
from app.core.config import settings
import time

logger = logging.getLogger(__name__)

# Try to import google.generativeai
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

@tool
def analyze_media_file(file_path: str, instruction: str = "Describe this file in detail.") -> str:
    """
    Analyzes a media file (image, audio, video) and returns a description or transcription.
    Use this tool when the user provides a local file path to a media file.
    
    Args:
        file_path: The absolute path to the local media file.
        instruction: Specific question or instruction about the file.
        
    Returns:
        The analysis result (transcription, description, etc.).
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    if not HAS_GENAI:
        return "Error: google-generativeai package not installed or import failed."
        
    if not settings.GOOGLE_API_KEY:
        return "Error: GOOGLE_API_KEY not configured."

    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        
        # Mime type detection
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            # Fallback based on extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.mp3', '.wav', '.ogg', '.m4a']:
                mime_type = 'audio/mp3' # Generic
            elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
                mime_type = 'video/mp4'
            elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
                mime_type = 'image/jpeg'
            elif ext in ['.pdf']:
                mime_type = 'application/pdf'
            elif ext in ['.txt', '.md', '.py', '.json', '.js', '.html', '.css', '.csv']:
                mime_type = 'text/plain'
            else:
                # Default for unknown
                mime_type = 'application/octet-stream'
        
        logger.info(f"Uploading file {file_path} ({mime_type}) to Gemini...")
        
        # Upload using the File API
        uploaded_file = genai.upload_file(file_path, mime_type=mime_type)
        
        # Wait for processing if it's video or large audio
        # Images are usually READY immediately
        while uploaded_file.state.name == "PROCESSING":
             time.sleep(2)
             uploaded_file = genai.get_file(uploaded_file.name)
             
        if uploaded_file.state.name == "FAILED":
             return "Error: File processing failed by Gemini API."

        # Model selection - use 1.5 Pro or Flash as they are multimodal
        # Default to Flash for speed, Pro for reasoning
        model_name = "gemini-1.5-flash" 
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content([uploaded_file, instruction])
        
        return response.text
        
    except Exception as e:
        logger.error(f"Error analyzing media: {e}")
        return f"Error analyzing media file: {str(e)}"

def get_media_tools():
    return [analyze_media_file]

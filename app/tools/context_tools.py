from langchain_core.tools import tool
from typing import List
import os
from app.core.models import AgentSession

def get_context_tools(session: AgentSession):
    
    @tool
    def add_context_file(file_path: str) -> str:
        """
        Adds a file to the continuous context window.
        Use this when a file is important and should be "remembered" for future turns.
        """
        # Normalize path
        abs_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_path):
            return f"Error: File {abs_path} does not exist."
            
        if abs_path not in session.context_files:
            session.context_files.append(abs_path)
            return f"Added {abs_path} to context files. content will be visible in the next turn."
        else:
            return f"File {abs_path} is already in context."

    @tool
    def remove_context_file(file_path: str) -> str:
        """
        Removes a file from the continuous context window.
        Use this when a file is no longer relevant to save tokens.
        """
        abs_path = os.path.abspath(file_path)
        if abs_path in session.context_files:
            session.context_files.remove(abs_path)
            return f"Removed {abs_path} from context."
        
        # Try finding by basename if full path fails
        for path in session.context_files:
            if os.path.basename(path) == file_path:
                session.context_files.remove(path)
                return f"Removed {path} from context."
                
        return f"File {file_path} not found in active context."

    @tool
    def list_context_files() -> str:
        """
        Lists all files currently pinned to the context window.
        """
        if not session.context_files:
            return "No files in active context."
        return "Active Context Files:\n" + "\n".join([f"- {path}" for path in session.context_files])

    return [add_context_file, remove_context_file, list_context_files]

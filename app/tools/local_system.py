from langchain.tools import tool
import subprocess
import os
import sys
from typing import Optional
from app.core.config import settings
from app.core.sandbox import sandbox

def _truncate(text: str, limit: int = 10000) -> str:
    if len(text) > limit:
        return text[:limit] + f"\n... [TRUNCATED {len(text)-limit} chars]"
    return text

@tool
def terminal(command: str) -> str:
    """
    Executes a shell command. Use this tool to run ANY terminal command.
    Do NOT simulate commands with text blocks.
    If SANDBOX_ENABLED is True, executes inside the Docker container (Linux).
    Otherwise, executes on the local host.
    """
    if settings.SANDBOX_ENABLED:
        try:
            # We assume the sandbox is Linux (bash/sh)
            exit_code, output = sandbox.exec_run(command)
            return f"Exit Code: {exit_code}\nOUTPUT:\n{_truncate(output)}"
        except Exception as e:
            return f"Sandbox Execution Error: {str(e)}"
    else:
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                encoding='utf-8',
                errors='replace',
                timeout=60
            )
            
            stdout = _truncate(result.stdout)
            stderr = _truncate(result.stderr)
            return f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        except Exception as e:
            return f"Error executing command: {str(e)}"

@tool
def run_powershell(script: str) -> str:
    """
    Executes a PowerShell script.
    WARNING: Not available in Sandbox Mode (Linux). Use 'terminal' for bash scripts.
    """
    if settings.SANDBOX_ENABLED:
        return "Error: run_powershell is not available in Docker Sandbox mode (Linux environment). Use 'terminal' for bash commands."

    import tempfile
    
    try:
        # Create a temporary ps1 file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ps1', encoding='utf-8') as f:
            f.write(script)
            temp_path = f.name
            
        executable = "powershell"
        command = [executable, "-ExecutionPolicy", "Bypass", "-File", temp_path]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60
        )
        
        # Cleanup
        try:
            os.remove(temp_path)
        except:
            pass
            
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        
    except Exception as e:
        return f"Error executing PowerShell script: {str(e)}"

@tool
def read_local_file(path: str) -> str:
    """Reads a file from the local file system (or Sandbox workspace volume). Large files are truncated."""
    if not os.path.exists(path):
        return "Error: File not found."
    try:
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."

        file_size = os.path.getsize(path)
        MAX_SIZE = 50 * 1024 # 50KB limit
        
        with open(path, "r", encoding="utf-8") as f:
            if file_size > MAX_SIZE:
                content = f.read(MAX_SIZE)
                return f"{content}\n... [TRUNCATED - File is {file_size/1024:.1f}KB. Use paging or tools like 'grep' to search content.]"
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def write_local_file(path: str, content: str) -> str:
    """Writes content to a file on the local file system (mirrored to Sandbox). This overwrites the entire file."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@tool
def replace_text_in_file(path: str, old_text: str, new_text: str) -> str:
    """
    Replaces a specific string in a file with a new string.
    Use this for surgical code edits instead of rewriting the whole file.
    Ensure 'old_text' is unique and matches exactly (including indentation).
    """
    if not os.path.exists(path):
        return "Error: File not found."
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if old_text not in content:
            return "Error: old_text not found in file. Check exact matching and indentation."
        
        if content.count(old_text) > 1:
            return "Error: old_text found multiple times. Be more specific to ensure unique match."
            
        new_content = content.replace(old_text, new_text)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        return f"Successfully patched {path}"
    except Exception as e:
        return f"Error patching file: {str(e)}"

@tool
def restore_repository(mode: str) -> str:
    """
    Restores the repository to a clean state using the restore.py script.
    
    Args:
        mode (str): 'soft' (revert changes, keep untracked) or 'hard' (reset to HEAD, delete everything).
    """
    valid_modes = ["soft", "hard"]
    if mode not in valid_modes:
        return f"Error: Invalid mode '{mode}'. Use 'soft' or 'hard'."

    try:
        # Determine root directory (app/tools/local_system.py -> ../../)
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        restore_script = os.path.join(root_dir, "restore.py")
        
        if not os.path.exists(restore_script):
             return f"Error: restore.py not found at {restore_script}"

        # Use the same python interpreter
        executable = sys.executable
        
        result = subprocess.run(
            [executable, restore_script, mode],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=root_dir
        )
        
        if result.returncode == 0:
            return f"Restoration ({mode}) successful.\nSTDOUT:\n{result.stdout}"
        else:
            return f"Restoration failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    except Exception as e:
        return f"Error running restoration: {str(e)}"

def get_local_tools():
    return [terminal, read_local_file, write_local_file, replace_text_in_file, run_powershell, restore_repository]


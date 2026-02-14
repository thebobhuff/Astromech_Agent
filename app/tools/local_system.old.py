from langchain.tools import tool
import subprocess
import os
from typing import Optional

@tool
def terminal(command: str) -> str:
    """
    Executes a shell command on the local system (PowerShell/Bash).
    Use this to run CLI tools, list directories, check system status, etc.
    Output is truncated if exceedingly long.
    """
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        
        stdout = result.stdout
        stderr = result.stderr
        MAX_LEN = 10000 
        
        if len(stdout) > MAX_LEN:
             stdout = stdout[:MAX_LEN] + "\n... [TRUNCATED STDOUT]"
        if len(stderr) > MAX_LEN:
             stderr = stderr[:MAX_LEN] + "\n... [TRUNCATED STDERR]"
             
        return f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

@tool
def run_powershell(script: str) -> str:
    """
    Executes a PowerShell script on Windows.
    Values are returned by printing them to stdout.
    The script content is saved to a temporary executable file and run.
    """
    import tempfile
    
    try:
        # Create a temporary ps1 file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ps1', encoding='utf-8') as f:
            f.write(script)
            temp_path = f.name
            
        # Execute it using PowerShell
        # Try pwsh (Core) first, then powershell (Desktop)
        executable = "powershell"
        
        # Check if pwsh is available (optional optimization, but powershell is standard on Windows)
        # We'll just stick to 'powershell' for now as it's built-in on Windows.
        
        command = [executable, "-ExecutionPolicy", "Bypass", "-File", temp_path]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
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
    """Reads a file from the local file system. Large files are truncated."""
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
    """Writes content to a file on the local file system. This overwrites the entire file."""
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

# Export list of tools
def get_local_tools():
    return [terminal, read_local_file, write_local_file, replace_text_in_file, run_powershell]


from langchain.tools import tool
import subprocess
import tempfile
import os
import sys

@tool
def run_python_code(code: str) -> str:
    """
    Executes a Python script in a separate process and returns the output (STDOUT/STDERR).
    Use this to run calculations, process data, or write custom logic to open/parse files that standard tools can't handle.
    
    The code runs on the host system (or container if sandboxed), having access to the local file system.
    Libraries available: standard library + installed packages (pandas, requests, etc.).
    
    Example:
    code = \"\"\"
    import json
    with open('data.json') as f:
        print(json.load(f)['key'])
    \"\"\"
    """
    try:
        # Create a temporary python file
        # We assume UTF-8 encoding
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py', encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
            
        # Use the same python interpreter as the running process
        executable = sys.executable
        
        # Run with timeout to prevent infinite loops (Increased to 60s for moderately complex tasks)
        result = subprocess.run(
            [executable, temp_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60 # 60s timeout
        )
        
        # Cleanup
        try:
            os.remove(temp_path)
        except:
            pass
            
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        output = ""
        if stdout:
            output += f"STDOUT:\n{stdout}\n"
        if stderr:
             output += f"STDERR:\n{stderr}\n"
             
        if not output:
            output = "Code executed successfully with no output."
            
        return output
        
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out (60s limit)."
    except Exception as e:
        return f"Error executing Python code: {str(e)}"

@tool
def install_python_package(package_name: str) -> str:
    """
    Installs a Python package using pip.
    Use this when you need a library that is not currently installed to solve a problem.
    
    Args:
        package_name: The name of the package to install (e.g., 'pandas', 'requests', 'beautifulsoup4').
    """
    try:
        executable = sys.executable
        
        # Run pip install
        # Timeout set to 300s (5 mins) as installation can be slow
        result = subprocess.run(
            [executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=300 
        )
        
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        if result.returncode == 0:
            return f"Successfully installed {package_name}.\nOutput:\n{stdout}"
        else:
            return f"Failed to install {package_name}.\nError:\n{stderr}"
            
    except subprocess.TimeoutExpired:
        return f"Error: Installation of {package_name} timed out."
    except Exception as e:
        return f"Error installing package: {str(e)}"

def get_code_tools():
    return [run_python_code, install_python_package]

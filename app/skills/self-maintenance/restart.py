import os
import sys
import subprocess
import time
import ctypes
import psutil

# Configuration
WORKSPACE_ROOT = os.getcwd() # Assumes run from root of workspace
VENV_PYTHON = os.path.join(WORKSPACE_ROOT, ".venv", "Scripts", "python.exe")
BACKEND_PORT = 13579
FRONTEND_PORT = 24680
BACKEND_CMD = [VENV_PYTHON, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", str(BACKEND_PORT)]
FRONTEND_DIR = os.path.join(WORKSPACE_ROOT, "frontend")
FRONTEND_CMD = ["npm", "run", "dev"]

def show_error(title, message):
    """Display a native Windows error dialog."""
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10) # 0x10 = MB_ICONERROR
    except Exception:
        print(f"ERROR [{title}]: {message}")

def kill_process_by_port(port):
    """Kills any process listening on the specified port."""
    killed = False
    print(f"Searching for processes on port {port}...")
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    print(f"Killing PID {proc.info['pid']} ({proc.info['name']})...")
                    proc.kill()
                    killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return killed

def check_port_bound(port, timeout=10):
    """Checks if a process successfully binds to the port within timeout."""
    start = time.time()
    while time.time() - start < timeout:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == port:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        time.sleep(1)
    return False

def main():
    try:
        print(">>> [ASTROMECH SELF-MAINTENANCE] Initiating Restart Sequence...")
        
        # 1. Kill existing services
        kill_process_by_port(FRONTEND_PORT)
        kill_process_by_port(BACKEND_PORT)
        
        # Give OS time to release file handles/ports
        time.sleep(3)
        
        # 2. Start Frontend
        print(">>> Launching Frontend (Next.js)...")
        # subprocess.CREATE_NEW_CONSOLE creates a new visible window
        subprocess.Popen(
            FRONTEND_CMD, 
            cwd=FRONTEND_DIR, 
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        # 3. Start Backend
        print(">>> Launching Backend (FastAPI)...")
        subprocess.Popen(
            BACKEND_CMD,
            cwd=WORKSPACE_ROOT,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        print(">>> Startup commands issued. Waiting for verification...")
        
        # 4. Verify Startup
        if check_port_bound(BACKEND_PORT, timeout=20):
            print(">>> Backend is UP.")
        else:
            raise Exception(f"Backend failed to bind port {BACKEND_PORT} within 20 seconds.")
            
        # Frontend takes longer, check casually
        if check_port_bound(FRONTEND_PORT, timeout=10):
            print(">>> Frontend seems to be starting.")
            
        print(">>> SUCCESS: System restart verified.")
        
    except Exception as e:
        err_str = str(e)
        print(f"!!! CRITICAL FAILURE: {err_str}")
        show_error("Astromech Restart Failed", f"The restart sequence encountered a critical error:\n\n{err_str}")
        sys.exit(1)

if __name__ == "__main__":
    if not os.path.exists(VENV_PYTHON):
        show_error("Configuration Error", f"Virtual Environment python not found at:\n{VENV_PYTHON}")
        sys.exit(1)
    main()

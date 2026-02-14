import sys
from pathlib import Path

# Ensure imports resolve regardless of current working directory.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    from app.main import app
    print("App imported successfully.")
    
    found = False
    for route in app.routes:
        if hasattr(route, "path") and "/models" in route.path:
            print(f"Found route: {route.path}")
            found = True
            
    if not found:
        print("ERROR: /models route NOT found in app.routes")
        # Print all paths to debug
        print("Available routes:")
        for route in app.routes:
            if hasattr(route, "path"):
                print(f" - {route.path}")
                
except Exception as e:
    print(f"CRITICAL ERROR importing app: {e}")
    import traceback
    traceback.print_exc()

import os
import sys
import subprocess
import time
import requests
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CDP_PORT = 9222
DEFAULT_PROFILE_NAME = "default"
BROWSER_DATA_DIR = Path("data/browser")

class BrowserLauncher:
    def __init__(self):
        self.executable_path: Optional[str] = None
        self.process: Optional[subprocess.Popen] = None
        self.cdp_port = DEFAULT_CDP_PORT
        
    def find_chrome_executable(self) -> Optional[str]:
        """Finds the Chrome executable on Windows."""
        if sys.platform != "win32":
            # Simple fallback for non-Windows (though user is on Windows)
            # You might want to extend this later
            return None
            
        candidates = []
        
        # Environment variables
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        
        # User Installs
        if local_app_data:
            candidates.append(os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"))
            candidates.append(os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"))
            candidates.append(os.path.join(local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"))

        # System Installs
        candidates.append(os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"))
        candidates.append(os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"))
        candidates.append(os.path.join(program_files, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"))
        candidates.append(os.path.join(program_files_x86, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"))
        candidates.append(os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"))
        candidates.append(os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"))

        for path in candidates:
            if os.path.exists(path):
                logger.info(f"Found browser executable: {path}")
                return path
                
        logger.error("No supported browser found.")
        return None

    def is_cdp_reachable(self, port: int) -> bool:
        """Checks if the Chrome DevTools Protocol is reachable on the given port."""
        try:
            response = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=1)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def launch(self, profile_name: str = DEFAULT_PROFILE_NAME, headless: bool = False) -> str:
        """
        Launches Chrome with a persistent profile and remote debugging enabled.
        Returns the CDP WebSocket URL.
        """
        
        # Check if already running on the port
        if self.is_cdp_reachable(self.cdp_port):
            logger.info(f"Browser already accessible on port {self.cdp_port}")
            return f"http://127.0.0.1:{self.cdp_port}"

        self.executable_path = self.find_chrome_executable()
        if not self.executable_path:
            raise FileNotFoundError("Could not find Chrome, Brave, or Edge executable.")

        user_data_dir = BROWSER_DATA_DIR / profile_name / "user-data"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        args = [
            self.executable_path,
            f"--remote-debugging-port={self.cdp_port}",
            f"--user-data-dir={user_data_dir.absolute()}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-sync",  # Prevent syncing with Google account automatically
            "--password-store=basic",
            # Optimization flags
            "--disable-background-networking",
            "--disable-component-update",
            "about:blank" # Open a blank page initially
        ]

        if headless:
             args.append("--headless=new")

        logger.info(f"Launching browser: {' '.join(str(s) for s in args)}")
        
        # Start the process
        # We don't pipe stdout/stderr to avoid blocking, but in production you might want to log them
        self.process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for CDP to be ready
        max_retries = 20
        for i in range(max_retries):
            if self.is_cdp_reachable(self.cdp_port):
                logger.info("Browser CDP is ready.")
                return f"http://127.0.0.1:{self.cdp_port}"
            time.sleep(0.5)
            
        raise TimeoutError("Browser failed to start CDP interface.")

    def stop(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

# Global instance
browser_launcher = BrowserLauncher()

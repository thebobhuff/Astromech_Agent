import docker
import os
import time
import tarfile
import io
from typing import Optional, Tuple
from app.core.config import settings

class DockerSandbox:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DockerSandbox, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.container = None
            # Lazy init - do not call _initialize() here to prevent import blocks
        return cls._instance
    
    def _initialize(self):
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
            print("Docker client connected.")
        except Exception as e:
            # Only print if we are actually trying to use it
            print(f"Warning: Docker not available: {e}")
            self.client = None

    def ensure_container_running(self):
        if not self.client:
            self._initialize()
            
        if not self.client:
            raise RuntimeError("Docker client not initialized. Is Docker Desktop running?")
            
        container_name = "astromech-runner"
        
        # Check if running
        try:
            self.container = self.client.containers.get(container_name)
            if self.container.status != "running":
                self.container.start()
        except docker.errors.NotFound:
            # Create it
            print(f"Creating sandbox container '{container_name}' from {settings.SANDBOX_IMAGE}...")
            # We mount the workspace to the sandbox so they share files?
            # Actually, true isolation would communicate via API or copy.
            # But for simplicity in Phase 2, let's use a volume mount or just copy.
            # Reference OpenClaw uses bind mounts for "Host Mode" but isolation for "Sandbox".
            # Let's bind mount the current workspace to /workspace for convenience, 
            # BUT this defeats the purpose of preventing file deletion if mapped rw.
            # A true sandbox should be ephemeral. 
            # HOWEVER, the user wants "tool execution" to compile/run things.
            # Let's START with mounting the workspace so we don't break existing workflows that expect persistence.
            # Safe mode: readonly mount? No, tools need write.
            # Let's bind mount the workspace to /workspace
            cwd = os.getcwd()
            self.container = self.client.containers.run(
                settings.SANDBOX_IMAGE,
                command="tail -f /dev/null", # Keep alive
                detach=True,
                name=container_name,
                full_restart=False, # Don't remove on exit
                volumes={cwd: {'bind': '/workspace', 'mode': 'rw'}},
                working_dir="/workspace",
                auto_remove=True
            )
            
    def exec_run(self, cmd: str, timeout: int = 60) -> Tuple[int, str]:
        """Runs a command and returns (exit_code, output)"""
        self.ensure_container_running()
        
        # Docker SDK exec_run doesn't support timeout natively in the same way subprocess does easily?
        # It has workdir option.
        try:
            exit_code, output = self.container.exec_run(
                cmd, 
                workdir="/workspace",
                demux=False # Combine stdout/stderr
            )
            return exit_code, output.decode('utf-8', errors='replace')
        except Exception as e:
            return -1, str(e)

    def read_file(self, path: str) -> str:
        """Reads a file from the container."""
        self.ensure_container_running()
        # Since we bind mount, we could just read local file. 
        # But if we want to be future proof for remote docker, we use exec cats.
        code, out = self.exec_run(f"cat {path}")
        if code != 0:
            raise FileNotFoundError(f"File {path} not found or unreadable: {out}")
        return out
        
    def write_file(self, path: str, content: str) -> str:
        """Writes file into container."""
        # For simplicity with bind mounts, we prefer local write if mounted.
        # But let's use the container execution to ensure permissions/users are consistent with container?
        # Actually writing via python inside container is safer for escaping.
        
        # Simple echo approach (fails on complex content)
        # Better: create temp file and copy, or use exec_run with python script
        
        # We'll use a python one-liner inside the container to write the file, avoiding shell escaping issues.
        import json
        json_content = json.dumps(content)
        python_cmd = f"python3 -c 'import json; open(\"{path}\", \"w\", encoding=\"utf-8\").write(json.loads({json_content}))'"
        code, out = self.exec_run(python_cmd)
        if code != 0:
             raise RuntimeError(f"Write failed: {out}")
        return f"Successfully wrote to {path}"

sandbox = DockerSandbox()

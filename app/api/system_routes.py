from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, List
import os
import asyncio
from app.core.config import settings
from app.core.logging_utils import broadcast_handler

router = APIRouter()

CORE_FILE = "CORE.md"
USER_FILE = "USER.md"
AGENTS_FILE = "AGENTS.md"
MEMORY_FILE = "MEMORY.md"
HEARTBEAT_FILE = "data/HEARTBEAT.md"
JUDGEMENT_FILE = "JUDGEMENT.md"

FILES = {
    "core": CORE_FILE,
    "user": USER_FILE,
    "agents": AGENTS_FILE,
    "memory": MEMORY_FILE,
    "heartbeat": HEARTBEAT_FILE,
    "judgement": JUDGEMENT_FILE
}

WHITELISTED_ENV_VARS = [
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USERS",
    "DISCORD_BOT_TOKEN",
    "WHATSAPP_API_TOKEN", "WHATSAPP_PHONE_ID",
    "EMAIL_SMTP_SERVER", "EMAIL_SMTP_PORT", "EMAIL_SENDER", "EMAIL_PASSWORD",
    "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER",
    # Allow LLM keys too since it's useful
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"
]

class SystemFile(BaseModel):
    content: str

class EnvSettings(BaseModel):
    settings: Dict[str, str]

@router.get("/files/{name}")
async def get_file(name: str):
    if name not in FILES:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = FILES[name]
    if not os.path.exists(file_path):
        return {"content": ""}
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/{name}")
async def update_file(name: str, file_data: SystemFile):
    if name not in FILES:
        raise HTTPException(status_code=404, detail="File not found")
        
    file_path = FILES[name]
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_data.content)
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/env")
async def get_env_settings():
    """Get safe list of environment variables."""
    current_settings = {}
    
    # helper: get from loaded settings or os.environ
    for key in WHITELISTED_ENV_VARS:
        val = getattr(settings, key, None)
        if val is None:
            val = os.getenv(key, "")
        if val is None:
            val = ""
        current_settings[key] = str(val)
        
    return current_settings

@router.post("/env")
async def update_env_settings(data: EnvSettings):
    """Update .env file and reload settings."""
    env_path = ".env"
    new_values = data.settings
    
    # 1. Read existing .env to preserve structure
    existing_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
             existing_lines = f.readlines()
    
    # 2. Update lines
    updated_lines = []
    processed_keys = set()
    
    for line in existing_lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#"):
            updated_lines.append(line)
            continue
            
        key = line_stripped.split("=", 1)[0].strip()
        if key in new_values:
            if key in WHITELISTED_ENV_VARS:
                updated_lines.append(f"{key}={new_values[key]}\n")
                processed_keys.add(key)
            else:
                updated_lines.append(line) # Don't touch non-whitelisted
        else:
            updated_lines.append(line)
            
    # 3. Append new keys that weren't in file
    for key, val in new_values.items():
        if key in WHITELISTED_ENV_VARS and key not in processed_keys:
            updated_lines.append(f"{key}={val}\n")
            
    # 4. Write back
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)
            
        # NOTE: This doesn't hot-reload the running process environment variables fully 
        # for things already initialized (like Bot instances), 
        # but a restart would pick them up.
        # Ideally we trigger a reload or user manually restarts.
        return {"status": "updated", "message": "Settings saved. Restart required for some changes."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    queue = await broadcast_handler.subscribe()
    try:
        while True:
            log_entry = await queue.get()
            await websocket.send_text(log_entry)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
        # Try to close if not already closed
        try:
            await websocket.close() 
        except: 
            pass
    finally:
        broadcast_handler.unsubscribe(queue)

@router.get("/status")
async def get_system_status():
    try:
        needs_onboarding = False
        
        # Check if USER.md is default/generic
        user_default_markers = ["**Name**: User", "Name: User"]
        
        if os.path.exists(USER_FILE):
            try:
                with open(USER_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                    if any(marker in content for marker in user_default_markers):
                        needs_onboarding = True
            except:
                pass # If error reading, assume okay or not generic
        else:
            needs_onboarding = True
            
        return {"needs_onboarding": needs_onboarding}
    except Exception as e:
        print(f"System status error: {e}")
        # If we can't determine status, default to needing onboarding to be safe, 
        # or false to avoid blocking if it's a transient error?
        # Returning error 500 blocks the UI. 
        # Let's return needs_onboarding=False but log it, so user can at least access the UI.
        return {"needs_onboarding": False}


@router.get("/heartbeat/status")
async def get_heartbeat_status():
    try:
        from app.main import heartbeat

        return heartbeat.get_runtime_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

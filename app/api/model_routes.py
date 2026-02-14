from fastapi import APIRouter, HTTPException
from typing import List
import logging
from app.core.models_config import load_models_config, save_models_config, LLMSystemConfig, ModelConfig

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=LLMSystemConfig)
async def get_config():
    return load_models_config()

@router.post("/", response_model=LLMSystemConfig)
async def update_config(config: LLMSystemConfig):
    save_models_config(config)
    return config

@router.get("/active", response_model=List[ModelConfig])
async def get_active_models():
    cfg = load_models_config()
    return [m for m in cfg.active_models if m.is_active]

@router.post("/refresh-ollama")
async def refresh_ollama_models():
    """Explicitly fetch available models from Ollama."""
    # This involves calling ollama /api/tags
    import requests
    from app.core.config import settings
    
    cfg = load_models_config()
    provider = cfg.providers.get("ollama")
    if not provider or not provider.enabled:
        logger.warning("Tagging refresh requested but Ollama provider is not enabled")
        raise HTTPException(status_code=400, detail="Ollama provider not enabled")
        
    try:
        base_url = provider.base_url or settings.OLLAMA_BASE_URL
        logger.info("Tagging refresh started: requesting Ollama tags from %s/api/tags", base_url)
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        logger.info("Tagging refresh response status=%s", resp.status_code)
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json().get('models', [])]
            provider.available_models = models
            cfg.providers["ollama"] = provider
            save_models_config(cfg)
            logger.info("Tagging refresh complete: %s model tags discovered", len(models))
            return {"status": "success", "models": models}
        logger.error("Tagging refresh failed: unexpected status code %s", resp.status_code)
    except Exception as e:
        logger.exception("Tagging refresh failed due to exception")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Ollama: {e}")
        
    return {"status": "error"}

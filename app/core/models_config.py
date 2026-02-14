import json
import logging
import os
from typing import Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

MODELS_CONFIG_PATH = os.path.join("data", "models.json")


class ModelConfig(BaseModel):
    provider: str
    name: str  # The internal name used by the agent (e.g., "fast_model")
    model_id: str  # The actual API model ID (e.g., "gemini-1.5-flash")
    description: Optional[str] = ""
    is_active: bool = True


class ProviderConfig(BaseModel):
    provider: str  # openai, gemini, anthropic, ollama, etc.
    enabled: bool = False
    api_key: Optional[str] = None  # Or use env var
    base_url: Optional[str] = None
    available_models: List[str] = []


class LLMSystemConfig(BaseModel):
    active_models: List[ModelConfig] = []
    providers: Dict[str, ProviderConfig] = {}
    default_model_name: str = "default"  # The name of the model to use by default

    def get_model(self, name: str) -> Optional[ModelConfig]:
        for model in self.active_models:
            if model.name == name:
                return model
        return None

    def get_default_model(self) -> Optional[ModelConfig]:
        return self.get_model(self.default_model_name)

    @classmethod
    def default(cls) -> "LLMSystemConfig":
        return cls(
            default_model_name="default",
            active_models=[
                ModelConfig(
                    provider="openrouter",
                    name="default",
                    model_id="arcee-ai/trinity-large-preview:free",
                    description="OpenRouter Trinity Large Preview primary model",
                ),
                ModelConfig(
                    provider="openrouter",
                    name="smart",
                    model_id="qwen/qwen3-vl-30b-a3b-thinking",
                    description="OpenRouter Qwen3 VL fallback model",
                ),
                ModelConfig(
                    provider="ollama",
                    name="local",
                    model_id="llama3",
                    description="Privacy focused, offline",
                ),
            ],
            providers={
                "gemini": ProviderConfig(
                    provider="gemini",
                    enabled=True,
                    available_models=["gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash"],
                ),
                "openai": ProviderConfig(
                    provider="openai",
                    enabled=False,
                    available_models=["gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o"],
                ),
                "anthropic": ProviderConfig(
                    provider="anthropic",
                    enabled=False,
                    available_models=[
                        "claude-3-opus-20240229",
                        "claude-3-sonnet-20240229",
                        "claude-3-haiku-20240307",
                    ],
                ),
                "ollama": ProviderConfig(provider="ollama", enabled=True, available_models=["llama3"]),
                "openrouter": ProviderConfig(
                    provider="openrouter",
                    enabled=True,
                    available_models=[
                        "arcee-ai/trinity-large-preview:free",
                        "z-ai/glm-4.7-flash",
                        "qwen/qwen3-vl-30b-a3b-thinking",
                        "openai/gpt-4o",
                        "anthropic/claude-3-opus",
                        "google/gemini-flash-1.5",
                    ],
                ),
                "deepseek": ProviderConfig(
                    provider="deepseek",
                    enabled=False,
                    available_models=["deepseek-chat", "deepseek-coder"],
                ),
                "kimi": ProviderConfig(
                    provider="kimi",
                    enabled=False,
                    base_url="https://api.moonshot.cn/v1",
                    available_models=["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
                ),
                "nvidia": ProviderConfig(
                    provider="nvidia",
                    enabled=True,
                    base_url="https://integrate.api.nvidia.com/v1",
                    available_models=["moonshotai/kimi-k2.5"],
                ),
            },
        )


def load_models_config() -> LLMSystemConfig:
    if not os.path.exists(MODELS_CONFIG_PATH):
        cfg = LLMSystemConfig.default()
        save_models_config(cfg)
        return cfg

    try:
        with open(MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = LLMSystemConfig(**data)

        default_config = LLMSystemConfig.default()
        merged = False
        for provider_name, provider_cfg in default_config.providers.items():
            if provider_name not in config.providers:
                config.providers[provider_name] = provider_cfg
                merged = True

        if merged:
            save_models_config(config)
        return config
    except Exception as exc:
        logger.error(f"Failed to load models config: {exc}")
        return LLMSystemConfig.default()


def save_models_config(config: LLMSystemConfig) -> None:
    os.makedirs(os.path.dirname(MODELS_CONFIG_PATH), exist_ok=True)
    with open(MODELS_CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(config.model_dump_json(indent=2))

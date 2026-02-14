from typing import Optional
import logging

from langchain_community.chat_models import ChatOllama
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

try:
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
except ImportError:
    ChatNVIDIA = None

from app.core.config import settings
from app.core.kimi_cli_chat import KimiCLIChatModel
from app.core.models_config import load_models_config

logger = logging.getLogger(__name__)


def get_llm(provider: Optional[str] = None, model_name: Optional[str] = None) -> BaseChatModel:
    """
    Factory function to return a configured LLM instance.
    Allows overriding provider and model for routing purposes.
    Checks models.json config first, then falls back to settings.
    """
    config = load_models_config()

    if not provider and not model_name:
        default_model = config.get_default_model()
        if default_model:
            provider = default_model.provider
            model_name = default_model.model_id

    provider_name = provider or settings.DEFAULT_LLM_PROVIDER
    provider_config = config.providers.get(provider_name)
    provider_type = provider_config.provider if provider_config else provider_name

    api_key = provider_config.api_key if provider_config else None
    base_url = provider_config.base_url if provider_config else None

    if not api_key:
        if provider_name == "openai":
            api_key = settings.OPENAI_API_KEY
        elif provider_name == "anthropic":
            api_key = settings.ANTHROPIC_API_KEY
        elif provider_name == "gemini":
            api_key = settings.GOOGLE_API_KEY
        elif provider_name == "openrouter":
            api_key = settings.OPENROUTER_API_KEY
        elif provider_name == "deepseek":
            api_key = settings.DEEPSEEK_API_KEY
        elif provider_name == "kimi":
            api_key = settings.KIMI_API_KEY
        elif provider_name == "nvidia":
            api_key = settings.NVIDIA_API_KEY

    if not base_url:
        if provider_name == "ollama":
            base_url = settings.OLLAMA_BASE_URL
        elif provider_name == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        elif provider_name == "deepseek":
            base_url = "https://api.deepseek.com"
        elif provider_name == "kimi":
            base_url = settings.KIMI_BASE_URL
        elif provider_name == "nvidia":
            base_url = settings.NVIDIA_BASE_URL

    if provider_type in {"openai", "openrouter", "deepseek"}:
        if not api_key:
            raise ValueError(f"API Key not found for provider {provider_name}")

        args = {
            "api_key": api_key,
            "model": model_name or "gpt-4-turbo",
        }
        if base_url:
            args["base_url"] = base_url

        return ChatOpenAI(**args)

    if provider_type == "anthropic":
        if not api_key:
            raise ValueError(f"API Key not found for provider {provider_name}")
        try:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                api_key=api_key,
                model_name=model_name or "claude-3-opus-20240229",
            )
        except ImportError as exc:
            raise ImportError("langchain-anthropic is not installed.") from exc

    if provider_type == "gemini":
        if not api_key:
            raise ValueError(f"API Key not found for provider {provider_name}")
        return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model_name or "gemini-2.5-flash",
            temperature=0.2,
        )

    if provider_type == "ollama":
        return ChatOllama(
            base_url=base_url or "http://localhost:11434",
            model=model_name or settings.OLLAMA_MODEL,
        )

    if provider_type == "kimi":
        resolved_model = model_name or "moonshot-v1-8k"
        if settings.KIMI_USE_CLI:
            return KimiCLIChatModel(
                cli_command=settings.KIMI_CLI_COMMAND,
                model=resolved_model,
                model_arg=settings.KIMI_CLI_MODEL_ARG,
                prompt_arg=settings.KIMI_CLI_PROMPT_ARG,
                extra_args=settings.KIMI_CLI_EXTRA_ARGS,
                timeout_seconds=settings.KIMI_CLI_TIMEOUT_SECONDS,
            )

        if not api_key:
            raise ValueError("API Key not found for provider kimi")

        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url or "https://api.moonshot.cn/v1",
            model=resolved_model,
        )

    if provider_type == "nvidia":
        if not api_key:
            raise ValueError("API Key not found for provider nvidia")

        resolved_model = model_name or settings.NVIDIA_MODEL
        resolved_base_url = base_url or settings.NVIDIA_BASE_URL

        # Prefer NVIDIA's native LangChain wrapper when available.
        # Fall back to OpenAI-compatible transport to avoid hard crashes if
        # the NVIDIA adapter package is missing in the runtime environment.
        if ChatNVIDIA is None:
            logger.warning(
                "langchain-nvidia-ai-endpoints is not installed; falling back to ChatOpenAI for nvidia provider."
            )
            return ChatOpenAI(
                api_key=api_key,
                base_url=resolved_base_url,
                model=resolved_model,
                temperature=settings.NVIDIA_TEMPERATURE,
                top_p=settings.NVIDIA_TOP_P,
                max_completion_tokens=settings.NVIDIA_MAX_COMPLETION_TOKENS,
            )

        args = {
            "model": resolved_model,
            "api_key": api_key,
            "temperature": settings.NVIDIA_TEMPERATURE,
            "top_p": settings.NVIDIA_TOP_P,
            "max_completion_tokens": settings.NVIDIA_MAX_COMPLETION_TOKENS,
        }
        if resolved_base_url:
            args["base_url"] = resolved_base_url
        return ChatNVIDIA(**args)

    # Fallback for custom OpenAI-compatible providers.
    if api_key and base_url:
        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model_name or "gpt-3.5-turbo",
        )

    raise ValueError(f"Unsupported LLM provider: {provider_name}")

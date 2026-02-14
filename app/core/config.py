from pydantic_settings import BaseSettings
from typing import Optional, Literal


class Settings(BaseSettings):
    PROJECT_NAME: str = "Astromech"
    API_V1_STR: str = "/api/v1"
    BACKEND_PORT: int = 13579

    # LLM Settings
    DEFAULT_LLM_PROVIDER: Literal[
        "openai", "anthropic", "ollama", "llamacpp", "gemini", "openrouter", "deepseek", "kimi", "nvidia"
    ] = "openrouter"

    # API Keys (Optional if using local models)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    NANO_BANANA_MODEL: str = "gemini-2.5-flash-image"
    DEEPSEEK_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    KIMI_API_KEY: Optional[str] = None
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "moonshotai/kimi-k2.5"
    NVIDIA_TEMPERATURE: float = 1.0
    NVIDIA_TOP_P: float = 1.0
    NVIDIA_MAX_COMPLETION_TOKENS: int = 16384
    KIMI_USE_CLI: bool = False
    KIMI_CLI_COMMAND: str = "kimi"
    KIMI_CLI_PROMPT_ARG: Optional[str] = None
    KIMI_CLI_MODEL_ARG: str = "--model"
    KIMI_CLI_EXTRA_ARGS: Optional[str] = None
    KIMI_CLI_TIMEOUT_SECONDS: int = 300
    BRAVE_SEARCH_API_KEY: Optional[str] = None

    # Local LLM Config
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    GENERATED_IMAGES_DIR: str = "data/generated_images"

    # Vector Store
    PERSIST_DIRECTORY: str = "./db"
    RELATIONSHIP_MEMORY_FILE: str = "data/memories/relationship/default_user.json"

    # Sandbox Settings
    SANDBOX_ENABLED: bool = False
    SANDBOX_IMAGE: str = "astromech-sandbox:latest"
    SANDBOX_TIMEOUT: int = 120

    # Agent execution safety timeouts
    AGENT_RUN_TIMEOUT_MS: int = 180000
    AGENT_LLM_TIMEOUT_SECONDS: int = 90
    AGENT_TOOL_TIMEOUT_SECONDS: int = 120
    AGENT_TOOL_RETRY_ATTEMPTS: int = 3
    AGENT_EXECUTION_MAX_ATTEMPTS: int = 4
    AGENT_REQUIRE_PLAN_APPROVAL: bool = False
    AGENT_MAX_CONCURRENT_RUNS: int = 2
    AGENT_QUEUE_WAIT_TIMEOUT_SECONDS: int = 300

    # Skills
    TELEGRAM_POLLING_ENABLED: bool = True
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ALLOWED_USERS: Optional[str] = None  # Comma separated list of user IDs
    DISCORD_BOT_TOKEN: Optional[str] = None

    # Future Channels
    WHATSAPP_API_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_ID: Optional[str] = None
    EMAIL_SMTP_SERVER: Optional[str] = None
    EMAIL_SMTP_PORT: Optional[int] = 587
    EMAIL_SENDER: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    TWILIO_ACCOUNT_SID: Optional[str] = None  # Phone
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # Local Node Runtime
    NODE_RUNTIME_ENABLED: bool = True
    NODE_RUNTIME_NAME: str = "Astromech Local Node"
    NODE_RUNTIME_ALLOW_SYSTEM_RUN: bool = False

    class Config:
        env_file = ".env"


settings = Settings()

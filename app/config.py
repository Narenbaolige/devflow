"""应用配置。"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """DevFlow 全局配置。"""

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///devflow.db")

    # LLM
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "chatanywhere")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")

    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "")

    CHATANYWHERE_API_KEY: str = os.getenv("CHATANYWHERE_API_KEY", "")
    CHATANYWHERE_BASE_URL: str = os.getenv(
        "CHATANYWHERE_BASE_URL", "https://api.chatanywhere.tech/v1"
    )

    # Docker
    DOCKER_IMAGE: str = os.getenv("DOCKER_IMAGE", "python:3.11-slim")
    SANDBOX_TIMEOUT_SECONDS: int = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "300"))
    SANDBOX_MAX_MEMORY_MB: int = int(os.getenv("SANDBOX_MAX_MEMORY_MB", "512"))
    SANDBOX_MAX_CPUS: int = int(os.getenv("SANDBOX_MAX_CPUS", "1"))

    # Agent
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "3"))
    AGENT_TIMEOUT_SECONDS: int = int(os.getenv("AGENT_TIMEOUT_SECONDS", "120"))

    # Debug
    DEVFLOW_DEBUG_CONTEXT: bool = os.getenv("DEVFLOW_DEBUG_CONTEXT", "0") == "1"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # 模型名称映射（按 provider）
    MODEL_MAP: dict = field(default_factory=lambda: {
        "openai": "gpt-4o-mini",
        "deepseek": "deepseek-chat",
        "chatanywhere": "gpt-4o-mini",
    })

    def get_model_name(self) -> str:
        return self.LLM_MODEL or self.MODEL_MAP.get(self.LLM_PROVIDER, "gpt-4o-mini")

    def get_api_key(self) -> str:
        key_map = {
            "openai": self.OPENAI_API_KEY,
            "deepseek": self.DEEPSEEK_API_KEY,
            "chatanywhere": self.CHATANYWHERE_API_KEY,
        }
        return key_map.get(self.LLM_PROVIDER, "")

    def get_base_url(self) -> str:
        url_map = {
            "openai": self.OPENAI_BASE_URL,
            "deepseek": self.DEEPSEEK_BASE_URL,
            "chatanywhere": self.CHATANYWHERE_BASE_URL,
        }
        return url_map.get(self.LLM_PROVIDER, "")


settings = Settings()

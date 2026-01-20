from dataclasses import dataclass
import os


@dataclass
class Settings:
    """
    Centralized configuration for the agent.
    Extend with more fields as needed.
    """

    app_name: str = os.getenv("APP_NAME", "AI Agent")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    history_limit: int = int(os.getenv("HISTORY_LIMIT", "20"))

    # GitHub Configuration
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_api_base: str = os.getenv("GITHUB_API_BASE", "https://api.github.com")

    # Gemini API Configuration
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")


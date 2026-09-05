import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Data Science Platform"
    API_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Auth & Security
    SECRET_KEY: str = "aidatascience-jwt-production-secret-key-3142921b"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = "sqlite:///./app.db"

    # File Storage Paths
    UPLOAD_DIR: str = "./data/uploads"
    PROCESSED_DIR: str = "./data/processed"
    RESULTS_DIR: str = "./data/results"
    MODEL_DIR: str = "./models/artifacts"
    SAMPLE_DIR: str = "./data/samples"

    # Upload Rules
    MAX_UPLOAD_SIZE: int = 104_857_600  # 100 MB
    ALLOWED_EXTENSIONS: set = {"csv", "xlsx", "xls"}

    # ML Configuration
    DEFAULT_RANDOM_SEED: int = 42
    DEFAULT_TEST_SIZE: float = 0.2
    DEFAULT_CV_FOLDS: int = 5
    MAX_OPTUNA_TRIALS: int = 100
    OPTUNA_TIMEOUT: int = 600  # seconds

    # AI / LLM / Groq Configuration
    GROQ_API_KEY: str = ""
    GROQ_CHAT_MODEL: str = "openai/gpt-oss-120b"
    GROQ_PROMPT_GUARD_MODEL: str = "meta-llama/llama-prompt-guard-2-86m"
    PROMPT_GUARD_THRESHOLD: float = 0.5
    PROMPT_GUARD_ENABLED: bool = True

    LLM_PROVIDER: str = "groq"  # "groq", "openai", "mock"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_BASE_URL: str = ""  # For OpenAI-compatible providers
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.1

    # Security & CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()

# Ensure directories exist
for directory in [
    settings.UPLOAD_DIR,
    settings.PROCESSED_DIR,
    settings.RESULTS_DIR,
    settings.MODEL_DIR,
    settings.SAMPLE_DIR,
]:
    os.makedirs(directory, exist_ok=True)

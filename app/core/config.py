from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application Metadata
    APP_NAME: str = "Enterprise AI Support Agent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Active LLM Provider Selection: "aurai" or "openrouter"
    LLM_PROVIDER: Literal["aurai", "openrouter"] = Field(
        default="aurai",
        description="Active LLM provider ('aurai' is primary, 'openrouter' is secondary)"
    )

    # Aurai Configuration (Primary)
    AURAI_API_KEY: str = Field(default="", description="Aurai Studio API Key")
    AURAI_BASE_URL: str = Field(
        default="https://api-pilot-sandbox.aurai.solutions/v1",
        description="Aurai API base URL"
    )
    AURAI_MODEL: str = Field(
        default="Aurai-3.0",
        description="Aurai model identifier"
    )
    AURAI_TEMPERATURE: float = 0.8
    AURAI_TOP_P: float = 0.1
    AURAI_MAX_TOKENS: int = 2048

    # OpenRouter Configuration (Secondary / Backup)
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API Key")
    OPENROUTER_BASE_URL: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL"
    )
    OPENROUTER_MODEL: str = Field(
        default="qwen/qwen-2.5-72b-instruct",
        description="OpenRouter model identifier"
    )

    # General LLM Parameters
    LLM_REQUEST_TIMEOUT: int = 15

    # Security & Authentication (JWT)
    JWT_SECRET_KEY: str = Field(
        default="insecure_default_secret_key_for_development_only_12345",
        description="Secret key for signing JWT tokens"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Qdrant Cloud Configuration
    QDRANT_URL: str = Field(
        default="",
        description="Qdrant Cloud cluster endpoint"
    )
    QDRANT_API_KEY: str = Field(
        default="",
        description="Qdrant Cloud API Key"
    )
    QDRANT_COLLECTION_NAME: str = Field(
        default="enterprise_knowledge",
        description="Qdrant collection name for IT knowledge base"
    )

    # Cloud Embeddings Configuration
    EMBEDDING_PROVIDER: str = Field(
        default="openrouter",
        description="Embeddings provider ('openrouter')"
    )
    EMBEDDING_MODEL: str = Field(
        default="openai/text-embedding-3-small",
        description="Cloud embedding model"
    )
    EMBEDDING_DIMENSION: int = Field(
        default=1536,
        description="Embedding vector dimensions"
    )

    # Supabase Relational Database (Phase 3)
    SUPABASE_URL: str = Field(
        default="",
        description="Supabase project URL"
    )
    SUPABASE_KEY: str = Field(
        default="",
        description="Supabase Service Role or Anon API Key"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

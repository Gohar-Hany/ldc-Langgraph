from functools import lru_cache
from typing import List, Literal
from pydantic import Field, field_validator
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
    # REQUIRED in production — no default; app will fail fast if missing or too short.
    JWT_SECRET_KEY: str = Field(
        default="",
        description="REQUIRED: Minimum 32-char secret key for signing JWT tokens. Must be set via environment."
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS Configuration (Whitelist specific origins — never use "*" with credentials)
    CORS_ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Whitelisted CORS origins. Set via comma-separated env var CORS_ALLOWED_ORIGINS."
    )

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

    # Tavily External Search Configuration (Phase 4)
    TAVILY_API_KEY: str = Field(
        default="",
        description="Tavily Search API Key"
    )
    TAVILY_SEARCH_DEPTH: str = Field(
        default="basic",
        description="Tavily search depth: basic or advanced"
    )
    TAVILY_TIMEOUT_SECONDS: int = Field(
        default=10,
        description="Tavily API request timeout in seconds"
    )
    TAVILY_MAX_RESULTS: int = Field(
        default=5,
        description="Maximum search results returned by Tavily"
    )

    # Phase 5: Productionization & Reliability
    RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        description="Enable API rate limiting middleware"
    )
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60,
        description="Maximum requests per minute per client IP"
    )
    METRICS_ENABLED: bool = Field(
        default=True,
        description="Enable telemetry and metrics collection"
    )

    # Phase 6: Distributed State Durability & Checkpointing
    DATABASE_URL: str = Field(
        default="",
        description="Direct PostgreSQL connection string for persistent checkpointer (e.g. Supabase pooler)"
    )
    CHECKPOINTER_BACKEND: Literal["postgres", "memory"] = Field(
        default="postgres",
        description="Checkpointer backend: 'postgres' for persistent DB storage or 'memory' for ephemeral testing"
    )

    # Phase 9: FinOps & Latency Optimization (Vector Semantic Caching)
    SEMANTIC_CACHE_ENABLED: bool = Field(
        default=True,
        description="Enable vector semantic caching for repeated and similar queries"
    )
    SEMANTIC_CACHE_THRESHOLD: float = Field(
        default=0.92,
        description="Minimum cosine similarity score required for a semantic cache hit"
    )
    SEMANTIC_CACHE_COLLECTION_NAME: str = Field(
        default="enterprise_semantic_cache",
        description="Qdrant collection name for storing semantic cache vectors"
    )
    SEMANTIC_CACHE_TTL_SECONDS: int = Field(
        default=604800,
        description="Time-To-Live in seconds for cached responses (default: 7 days)"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def validate_production_secrets() -> None:
    """
    Called at startup to enforce critical security invariants in production.
    Raises SystemExit immediately if any required secret is missing or insecure.
    """
    if settings.ENVIRONMENT == "production":
        if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32:
            raise SystemExit(
                "FATAL: JWT_SECRET_KEY must be at least 32 characters in production. "
                "Set it via the JWT_SECRET_KEY environment variable."
            )
        if "*" in settings.CORS_ALLOWED_ORIGINS:
            raise SystemExit(
                "FATAL: CORS_ALLOWED_ORIGINS must not contain '*' in production. "
                "Set explicit allowed origins via the CORS_ALLOWED_ORIGINS environment variable."
            )

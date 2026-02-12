"""
Configuration management for Enterprise Memory Infrastructure Phase 2.
Strict validation with fail-fast behavior.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ========================================================================
    # DATABASE CONFIGURATION
    # ========================================================================
    database_url: str = Field(..., env="DATABASE_URL")
    
    # ========================================================================
    # REDIS CONFIGURATION (Phase 2 Scalability)
    # ========================================================================
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # ========================================================================
    # EXTRACTION PROVIDER CONFIGURATION (Phase 2)
    # ========================================================================
    extraction_provider: str = Field(default="openai", env="EXTRACTION_PROVIDER")
    
    # Chat provider (optional, defaults to extraction_provider)
    chat_provider: Optional[str] = Field(default=None, env="CHAT_PROVIDER")
    
    # OpenAI
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    
    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-5-sonnet-20241022", env="ANTHROPIC_MODEL")
    
    # Gemini
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", env="GEMINI_MODEL")
    gemini_max_input_tokens: int = Field(default=8000, env="GEMINI_MAX_INPUT_TOKENS")
    gemini_max_output_tokens: int = Field(default=1024, env="GEMINI_MAX_OUTPUT_TOKENS")
    
    # Local LLM
    local_llm_endpoint: Optional[str] = Field(default=None, env="LOCAL_LLM_ENDPOINT")
    local_llm_model: str = Field(default="llama2", env="LOCAL_LLM_MODEL")
    
    # Provider fallback
    provider_fallback_enabled: bool = Field(default=False, env="PROVIDER_FALLBACK_ENABLED")
    
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
    api_key: str = Field(..., env="API_KEY")
    
    # ========================================================================
    # SECURITY SETTINGS (V1.1)
    # ========================================================================
    cors_origins: str = Field(default="http://localhost:3000", env="CORS_ORIGINS")
    max_request_size: int = Field(default=1048576, env="MAX_REQUEST_SIZE")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    
    # ========================================================================
    # ENCRYPTION (Phase 2)
    # ========================================================================
    field_encryption_enabled: bool = Field(default=False, env="FIELD_ENCRYPTION_ENABLED")
    encryption_key: Optional[str] = Field(default=None, env="ENCRYPTION_KEY")
    
    # ========================================================================
    # OBSERVABILITY (Phase 2)
    # ========================================================================
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    structured_logging: bool = Field(default=True, env="STRUCTURED_LOGGING")
    
    # ========================================================================
    # TTL CLEANUP (Phase 2)
    # ========================================================================
    ttl_cleanup_interval: int = Field(default=3600, env="TTL_CLEANUP_INTERVAL")
    
    # ========================================================================
    # LOCK CONTENTION (Phase 2 Scalability)
    # ========================================================================
    lock_max_retries: int = Field(default=3, env="LOCK_MAX_RETRIES")
    lock_retry_delay_ms: int = Field(default=100, env="LOCK_RETRY_DELAY_MS")
    
    # ========================================================================
    # APPLICATION SETTINGS
    # ========================================================================
    app_name: str = Field(default="Memory Infrastructure Phase 2", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="production", env="ENVIRONMENT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator("database_url")
    def validate_database_url(cls, v):
        """Ensure DATABASE_URL is valid PostgreSQL connection string."""
        if not v or not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string")
        return v
    
    @validator("extraction_provider")
    def validate_extraction_provider(cls, v):
        """Ensure extraction provider is supported."""
        valid_providers = ["openai", "anthropic", "gemini", "local"]
        if v.lower() not in valid_providers:
            raise ValueError(f"EXTRACTION_PROVIDER must be one of: {valid_providers}")
        return v.lower()
    
    @validator("chat_provider")
    def validate_chat_provider(cls, v):
        """Ensure chat provider is supported if specified."""
        if v is None:
            return v
        valid_providers = ["openai", "anthropic", "gemini", "local"]
        if v.lower() not in valid_providers:
            raise ValueError(f"CHAT_PROVIDER must be one of: {valid_providers}")
        return v.lower()
    
    @validator("openai_api_key")
    def validate_openai_key(cls, v, values):
        """Ensure OpenAI API key is valid if using OpenAI provider."""
        provider = values.get("extraction_provider", "openai")
        if provider == "openai" and (not v or len(v) < 20):
            raise ValueError("OPENAI_API_KEY required when using OpenAI provider")
        return v
    
    @validator("api_key")
    def validate_api_key(cls, v):
        """Ensure API key is not empty."""
        if not v or len(v) < 16:
            raise ValueError("API_KEY must be at least 16 characters")
        return v
    
    @validator("cors_origins")
    def validate_cors_origins(cls, v):
        """Validate CORS origins."""
        if "*" in v:
            raise ValueError("CORS wildcard (*) not allowed. Specify explicit origins.")
        return v
    
    @validator("encryption_key")
    def validate_encryption_key(cls, v, values):
        """Validate encryption key if encryption enabled."""
        if values.get("field_encryption_enabled") and not v:
            raise ValueError("ENCRYPTION_KEY required when field encryption is enabled")
        return v
    
    def get_cors_origins_list(self) -> list:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    def get_chat_provider(self) -> str:
        """Get chat provider, falling back to extraction provider if not set."""
        return self.chat_provider if self.chat_provider else self.extraction_provider


# Global settings instance
settings = Settings()

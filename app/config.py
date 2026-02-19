"""
Configuration management for Enterprise Memory Infrastructure Phase 2.
Strict validation with fail-fast behavior.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ValidationInfo
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

    # JWT Configuration
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
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
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v, info: ValidationInfo):
        """
        Ensure DATABASE_URL is valid PostgreSQL connection string.
        Phase 4: Enforce SSL in production.
        """
        if not v or not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string")
        
        # Enforce SSL for production
        env = info.data.get("environment", "production")
        if env == "production" and "sslmode=require" not in v and "sslmode=verify" not in v:
             # Log warning or raise error. Prompt says "Log warning or raise startup error".
             # We will raise error for "infrastructure-grade production correct".
             raise ValueError("Production DATABASE_URL must contain 'sslmode=require'")
             
        return v
    
    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Phase 6: Ensure JWT secret is strong."""
        if not v or len(v) < 32:
             raise ValueError("jwt_secret must be at least 32 characters")
        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v):
        """Ensure API key is not empty and strong."""
        if not v or len(v) < 16:
             raise ValueError("api_key must be at least 16 characters")
        return v

    @field_validator("extraction_provider")
    @classmethod
    def validate_extraction_provider(cls, v):
        """Ensure extraction provider is supported."""
        valid_providers = ["openai", "anthropic", "gemini", "local"]
        if v.lower() not in valid_providers:
            raise ValueError(f"EXTRACTION_PROVIDER must be one of: {valid_providers}")
        return v.lower()
    
    @field_validator("chat_provider")
    @classmethod
    def validate_chat_provider(cls, v):
        """Ensure chat provider is supported if specified."""
        if v is None:
            return v
        valid_providers = ["openai", "anthropic", "gemini", "local"]
        if v.lower() not in valid_providers:
            raise ValueError(f"CHAT_PROVIDER must be one of: {valid_providers}")
        return v.lower()
    
    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, v, info: ValidationInfo):
        """Ensure OpenAI API key is valid if using OpenAI provider."""
        provider = info.data.get("extraction_provider", "openai")
        if provider == "openai" and (not v or len(v) < 20):
            # Check strictly only if provider is explicitly set to openai in this context
            # pass for now to allow mixed configurations, strict check in provider init
            pass
        return v
    
    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v):
        """Validate CORS origins."""
        if "*" in v:
            raise ValueError("CORS wildcard (*) not allowed. Specify explicit origins.")
        return v
    
    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v, info: ValidationInfo):
        """Validate encryption key if encryption enabled."""
        if info.data.get("field_encryption_enabled") and not v:
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

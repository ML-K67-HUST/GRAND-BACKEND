import os
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Environment(str, Enum):
    """Application environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    host: str = Field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    port: int = Field(default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432")))
    user: str = Field(default_factory=lambda: os.getenv("POSTGRES_USER", "timenest"))
    password: str = Field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "timenest_password_123"))
    db: str = Field(default_factory=lambda: os.getenv("POSTGRES_DB", "timenest"))
    
    # Connection pool settings
    pool_size: int = Field(20, env="DB_POOL_SIZE")
    max_overflow: int = Field(30, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(3600, env="DB_POOL_RECYCLE")
    
    @property
    def url(self) -> str:
        """Database connection URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
    
    @property
    def async_url(self) -> str:
        """Async database connection URL"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,  # Make case sensitive to avoid conflicts
        "env_prefix": ""  # Ensure no prefix conflicts
    }


class RedisSettings(BaseSettings):
    """Redis configuration settings"""
    host: str = Field("localhost", env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    db: int = Field(0, env="REDIS_DB")
    
    @property
    def url(self) -> str:
        """Redis connection URL"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


class JWTSettings(BaseSettings):
    """JWT configuration settings"""
    secret_key: str = Field("your-super-secret-jwt-key-at-least-32-chars-long", env="JWT_SECRET_KEY")
    refresh_secret_key: str = Field("your-super-secret-refresh-key-at-least-32-chars-long", env="JWT_REFRESH_SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    @field_validator('secret_key', 'refresh_secret_key')
    @classmethod
    def validate_secret_keys(cls, v):
        if len(v) < 32:
            raise ValueError('Secret keys must be at least 32 characters long')
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


class SecuritySettings(BaseSettings):
    """Security configuration settings"""
    secret_key: str = Field("your-super-secret-application-key-at-least-32-chars-long", env="SECRET_KEY")
    cors_origins: str = Field('["*"]', env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: str = Field('["*"]', env="CORS_ALLOW_METHODS")
    cors_allow_headers: str = Field('["*"]', env="CORS_ALLOW_HEADERS")
    
    # Security flags
    security_enabled: bool = Field(True, env="SECURITY_ENABLED")
    rate_limit_enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string"""
        import json
        try:
            return json.loads(self.cors_origins)
        except json.JSONDecodeError:
            return ["*"]
    
    @property
    def cors_methods_list(self) -> List[str]:
        """Parse CORS methods from JSON string"""
        import json
        try:
            return json.loads(self.cors_allow_methods)
        except json.JSONDecodeError:
            return ["*"]
    
    @property
    def cors_headers_list(self) -> List[str]:
        """Parse CORS headers from JSON string"""
        import json
        try:
            return json.loads(self.cors_allow_headers)
        except json.JSONDecodeError:
            return ["*"]
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


class GoogleOAuthSettings(BaseSettings):
    """Google OAuth configuration settings"""
    client_id: str = Field("", env="GOOGLE_CLIENT_ID")
    client_secret: str = Field("", env="GOOGLE_CLIENT_SECRET")
    redirect_uri: str = Field("http://127.0.0.1:5050/auth", env="GOOGLE_REDIRECT_URI")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


class ExternalServicesSettings(BaseSettings):
    """External services configuration settings"""
    together_api_key: Optional[str] = Field(None, env="TOGETHER_AI_API_KEY")
    chroma_endpoint: Optional[str] = Field(None, env="CHROMA_CLIENT_URL")
    embedding_client_url: Optional[str] = Field(None, env="EMBEDDING_CLIENT_URL")
    frontend_url: str = Field("http://127.0.0.1:3000", env="FRONTEND_URL")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


class Settings(BaseSettings):
    """Main application settings with nested configuration objects"""
    
    # Application settings
    app_name: str = Field("TimeNest Backend", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    log_level: LogLevel = Field(LogLevel.INFO, env="LOG_LEVEL")
    
    # Server settings
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(5050, env="PORT")
    reload: bool = Field(False, env="RELOAD")
    
    # Nested configuration objects
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    jwt: JWTSettings = JWTSettings()
    security: SecuritySettings = SecuritySettings()
    google_oauth: GoogleOAuthSettings = GoogleOAuthSettings()
    external_services: ExternalServicesSettings = ExternalServicesSettings()
    
    @model_validator(mode='after')
    def validate_environment_settings(self):
        """Validate environment-specific settings"""
        if self.environment == Environment.PRODUCTION:
            if self.debug:
                raise ValueError('Debug mode cannot be enabled in production')
        return self
    
    # Backward compatibility properties
    @property
    def database_url(self) -> str:
        """Database connection URL - backward compatibility"""
        return self.database.url
    
    @property
    def database_async_url(self) -> str:
        """Async database connection URL - backward compatibility"""
        return self.database.async_url
    
    @property
    def redis_url(self) -> str:
        """Redis connection URL - backward compatibility"""
        return self.redis.url
    
    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_staging(self) -> bool:
        return self.environment == Environment.STAGING
    
    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings() 
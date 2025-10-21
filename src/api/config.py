"""
Configuration for Resume Parser API
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_TITLE: str = "Resume Parser API"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # Model Settings
    MODEL_PATH: str = "./ml_model"
    
    # Processing Settings
    MAX_BATCH_SIZE: int = 100
    MAX_FILE_SIZE_MB: int = 10
    WORKER_THREADS: int = 4
    
    # Temp File Settings
    TEMP_DIR: Optional[str] = None
    CLEANUP_TEMP_FILES: bool = True
    
    # CORS Settings
    CORS_ORIGINS: list = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

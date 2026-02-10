"""
Configuration module for Bandcamp Code Verificator.
"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Config:
    """Application configuration."""
    
    # API Settings
    API_URL = "https://bandcamp.com/api/codes/1/verify"
    VERIFY_URL = API_URL
    TIMEOUT = 25
    HTTP2_ENABLED = True
    
    # Rate Limiting
    MIN_DELAY_SEC = 1
    MAX_DELAY_SEC = 5
    
    # Limits
    MAX_CODES = 2000
    MAX_CODE_LENGTH = 256
    MAX_CRUMB_LENGTH = 512
    MAX_CLIENT_ID_LENGTH = 128
    MAX_SESSION_LENGTH = 4096
    
    # Headers
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0"
    
    # Logging
    LOG_FILE = "verificator.log"
    LOG_FORMAT = "json"  # json or text
    LOG_LEVEL = "INFO"
    
    # Security
    CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    EXPORT_FOLDER = BASE_DIR / "exports"
    
    # Flask Web Settings
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())
    FLASK_ENV = os.environ.get("FLASK_ENV", "production")
    DEBUG = FLASK_ENV == "development"
    HOST = "127.0.0.1"
    PORT = 5000
    
    # Bandcamp Credentials (from .env file)
    BANDCAMP_CRUMB = os.environ.get("BANDCAMP_CRUMB", "")
    BANDCAMP_CLIENT_ID = os.environ.get("BANDCAMP_CLIENT_ID", "")
    BANDCAMP_SESSION = os.environ.get("BANDCAMP_SESSION", "")
    
    @classmethod
    def has_credentials(cls) -> bool:
        """Check if credentials are configured.
        
        Returns:
            True if all credentials are set
        """
        return bool(
            cls.BANDCAMP_CRUMB and 
            cls.BANDCAMP_CLIENT_ID and 
            cls.BANDCAMP_SESSION
        )
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if present
        for key in dir(cls):
            if key.isupper():
                env_value = os.environ.get(key)
                if env_value is not None:
                    setattr(config, key, env_value)
        
        return config
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration values."""
        if cls.MIN_DELAY_SEC > cls.MAX_DELAY_SEC:
            raise ValueError("MIN_DELAY_SEC cannot be greater than MAX_DELAY_SEC")
        
        if cls.TIMEOUT < 1:
            raise ValueError("TIMEOUT must be at least 1 second")
        
        if cls.MAX_CODES < 1:
            raise ValueError("MAX_CODES must be at least 1")
        
        return True

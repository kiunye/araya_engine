from pydantic_settings import BaseSettings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    GOOGLE_API_KEY: Optional[str] = None
    DEEPGRAM_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_INDEX_NAME: str = "araya-research"
    PINECONE_ENVIRONMENT: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    
    # Vector Store
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "araya-research"
    QDRANT_TIMEOUT: int = 30  # Request timeout in seconds
    
    # HTTP Client Configuration
    HTTP_REQUEST_TIMEOUT: int = 30  # Default timeout for HTTP requests
    HTTP_SEARCH_TIMEOUT: int = 10   # Timeout for search API requests
    HTTP_FETCH_TIMEOUT: int = 15    # Timeout for page fetching
    
    # Model Configuration
    GEMINI_FLASH_MODEL: str = "gemini-1.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-1.5-pro"
    
    # Research Configuration
    MAX_FINDINGS_PER_AGENT: int = 50
    MAX_RETRY_COUNT: int = 3
    REPORT_MAX_TOKENS: int = 8192
    
    class Config:
        env_file = ".env"
        extra = "allow"
    
    def validate_required_settings(self):
        """Validate that required settings are present."""
        required_settings = [
            ("GOOGLE_API_KEY", self.GOOGLE_API_KEY),
            ("SERPER_API_KEY", self.SERPER_API_KEY),
            ("DATABASE_URL", self.DATABASE_URL),
        ]
        
        missing = []
        for name, value in required_settings:
            if not value:
                missing.append(name)
        
        if missing:
            logger.warning(f"Missing required settings: {', '.join(missing)}")
            return False
        return True

settings = Settings()

# Validate settings on import
try:
    settings.validate_required_settings()
except Exception as e:
    logger.warning(f"Settings validation failed: {e}")
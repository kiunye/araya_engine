from pydantic_settings import BaseSettings
from typing import Optional

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

settings = Settings()
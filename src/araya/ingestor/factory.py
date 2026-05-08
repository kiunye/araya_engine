from typing import Optional
from pathlib import Path
from araya.ingestor.models import ResearchObject, SourceType
from araya.ingestor.pdf import PDFIngestor
from araya.ingestor.audio import AudioIngestor
from araya.ingestor.image import ImageIngestor
from araya.ingestor.web import WebIngestor

class MultimodalIngestor:
    """
    Unified ingestor that delegates to specialized ingestors based on file type.
    """
    
    INGESTOR_MAP = {
        ".pdf": PDFIngestor,
        ".mp3": AudioIngestor,
        ".wav": AudioIngestor,
        ".m4a": AudioIngestor,
        ".mp4": AudioIngestor,
        ".png": ImageIngestor,
        ".jpg": ImageIngestor,
        ".jpeg": ImageIngestor,
        ".gif": ImageIngestor,
    }
    
    def __init__(self, api_keys: Optional[dict] = None):
        self.api_keys = api_keys or {}
        self.pdf_ingestor = PDFIngestor()
        self.audio_ingestor = AudioIngestor(api_key=self.api_keys.get("deepgram"))
        self.image_ingestor = ImageIngestor(api_key=self.api_keys.get("google"))
        self.web_ingestor = WebIngestor()
    
    def ingest(self, file_path: str, metadata: Optional[dict] = None) -> ResearchObject:
        """
        Auto-detect file type and delegate to appropriate ingestor.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == ".pdf":
            return self.pdf_ingestor.ingest(file_path, metadata)
        elif suffix in {".mp3", ".wav", ".m4a", ".mp4"}:
            return self.audio_ingestor.ingest(file_path, metadata)
        elif suffix in {".png", ".jpg", ".jpeg", ".gif"}:
            return self.image_ingestor.ingest(file_path, metadata)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    
    async def ingest_url(self, url: str, metadata: Optional[dict] = None) -> ResearchObject:
        """Ingest a web URL."""
        return await self.web_ingestor.ingest(url, metadata)
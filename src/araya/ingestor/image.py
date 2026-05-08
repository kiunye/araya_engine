import uuid
import os
from typing import Optional
import google.generativeai as genai
from araya.ingestor.models import ResearchObject, SourceType
from araya.core.config import settings

class ImageIngestor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_API_KEY
        if not self.api_key:
            raise ValueError("Google API key is required for image ingestion")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def ingest(self, file_path: str, metadata: Optional[dict] = None) -> ResearchObject:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Load the image
        with open(file_path, "rb") as f:
            image_data = f.read()
        
        # Prepare the prompt
        prompt = "Describe this image in detail for a research report. Extract any text, data, or key information visible."
        
        response = self.model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": image_data}  # Simplified mime_type
        ])
        
        content = response.text

        # Prepare metadata
        obj_metadata = {
            "filename": os.path.basename(file_path),
        }
        if metadata:
            obj_metadata.update(metadata)

        return ResearchObject(
            id=str(uuid.uuid4()),
            source_type=SourceType.IMAGE,
            content=content,
            metadata=obj_metadata,
            elements=[]
        )
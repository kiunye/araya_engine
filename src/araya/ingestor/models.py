from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class SourceType(str, Enum):
    PDF = "pdf"
    AUDIO = "audio"
    IMAGE = "image"
    WEB = "web"

class MultimodalElement(BaseModel):
    type: str  # "table", "image", "chart"
    content: str  # Markdown representation or description
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ref: Optional[str] = None  # Reference to original file or storage path

class ResearchObject(BaseModel):
    id: str
    source_type: SourceType
    content: str  # Unified markdown representation
    metadata: Dict[str, Any] = Field(default_factory=dict)
    elements: List[MultimodalElement] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
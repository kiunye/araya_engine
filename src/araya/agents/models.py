from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, computed_field
from enum import Enum
import uuid


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: f"finding_{uuid.uuid4().hex[:8]}")
    claim: str = Field(..., description="The factual statement or data point")
    source_doc_id: Optional[str] = None
    source_page: Optional[int] = None
    source_url: Optional[str] = None
    source_excerpt: str = ""
    confidence: Confidence = Confidence.MEDIUM
    verified: bool = False
    verified_against: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @computed_field
    @property
    def source_id(self) -> str:
        return self.source_url or self.source_doc_id or "unknown"

    @computed_field
    @property
    def content(self) -> str:
        return self.claim


class ResearchPlanItem(BaseModel):
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:6]}")
    description: str
    status: str = "pending"
    assigned_to: Optional[str] = None
    result: Optional[str] = None


class EvaluationScore(BaseModel):
    grounding_score: float = Field(..., ge=0, le=10)
    completeness_score: float = Field(..., ge=0, le=10)
    feedback: str
    passed: bool

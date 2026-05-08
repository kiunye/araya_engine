import uuid
import os
import json
import re
import logging
from typing import List, Dict, Any, Optional, TypedDict
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from araya.agents.state import ResearchState
from araya.agents.models import Finding, Confidence
from araya.ingestor.models import ResearchObject
from araya.agents.lead_agent import get_model

logger = logging.getLogger(__name__)


class DocumentAnalystResult(TypedDict):
    findings: List[Finding]
    research_objects: List[ResearchObject]
    analysis_summary: str


class DocumentAnalystAgent:
    def __init__(self):
        self.pdf_ingestor = None
        self.audio_ingestor = None
        self.image_ingestor = None
        self.model = get_model("gemini-1.5-flash")

    def _get_pdf_ingestor(self):
        if self.pdf_ingestor is None:
            from araya.ingestor.pdf import PDFIngestor
            self.pdf_ingestor = PDFIngestor()
        return self.pdf_ingestor

    def _get_audio_ingestor(self):
        if self.audio_ingestor is None:
            from araya.ingestor.audio import AudioIngestor
            self.audio_ingestor = AudioIngestor()
        return self.audio_ingestor

    def _get_image_ingestor(self):
        if self.image_ingestor is None:
            from araya.ingestor.image import ImageIngestor
            self.image_ingestor = ImageIngestor()
        return self.image_ingestor

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        objective = state.get("objective", "")
        files = state.get("files", [])
        all_findings = []

        if not files:
            logger.info("DocumentAnalystAgent: No files provided, skipping.")
            return {"findings": []}

        for file_path in files:
            try:
                if file_path.endswith(".pdf"):
                    result = await self.analyze_pdf(file_path, objective)
                elif file_path.endswith((".mp3", ".wav", ".m4a", ".mp4")):
                    result = await self.transcribe_audio(file_path, objective)
                elif file_path.endswith((".png", ".jpg", ".jpeg", ".gif")):
                    result = await self.describe_image(file_path, objective)
                else:
                    continue
                all_findings.extend(result.get("findings", []))
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")

        return {"findings": all_findings}

    async def analyze_pdf(self, file_path: str, analysis_objective: str) -> DocumentAnalystResult:
        if not os.path.exists(file_path):
            return self._error_result(f"PDF file not found: {file_path}")

        try:
            ingestor = self._get_pdf_ingestor()
            research_obj = ingestor.ingest(file_path)

            findings = await self._extract_findings_from_content(
                content=research_obj.content,
                source_doc_id=research_obj.id,
                source_type="pdf",
                analysis_objective=analysis_objective,
                metadata=research_obj.metadata
            )

            table_findings = self._extract_table_findings(research_obj)
            findings.extend(table_findings)

            return {
                "findings": findings,
                "research_objects": [research_obj],
                "analysis_summary": f"Analyzed PDF: {Path(file_path).name}, extracted {len(findings)} findings"
            }
        except Exception as e:
            return self._error_result(f"Error analyzing PDF: {str(e)}")

    async def transcribe_audio(self, file_path: str, analysis_objective: str) -> DocumentAnalystResult:
        if not os.path.exists(file_path):
            return self._error_result(f"Audio file not found: {file_path}")

        try:
            ingestor = self._get_audio_ingestor()
            research_obj = ingestor.ingest(file_path)

            findings = await self._extract_findings_from_content(
                content=research_obj.content,
                source_doc_id=research_obj.id,
                source_type="audio",
                analysis_objective=analysis_objective,
                metadata=research_obj.metadata
            )

            return {
                "findings": findings,
                "research_objects": [research_obj],
                "analysis_summary": f"Transcribed audio: {Path(file_path).name}"
            }
        except Exception as e:
            return self._error_result(f"Error transcribing audio: {str(e)}")

    async def describe_image(self, file_path: str, analysis_objective: str) -> DocumentAnalystResult:
        if not os.path.exists(file_path):
            return self._error_result(f"Image file not found: {file_path}")

        try:
            ingestor = self._get_image_ingestor()
            research_obj = ingestor.ingest(file_path)

            finding = Finding(
                id=f"finding_{uuid.uuid4().hex[:8]}",
                claim=f"Visual content from {Path(file_path).name}: {research_obj.content[:500]}",
                source_doc_id=research_obj.id,
                source_excerpt=research_obj.content,
                confidence=Confidence.MEDIUM,
                metadata={"filename": Path(file_path).name, "source_type": "image"}
            )

            return {
                "findings": [finding],
                "research_objects": [research_obj],
                "analysis_summary": f"Described image: {Path(file_path).name}"
            }
        except Exception as e:
            return self._error_result(f"Error describing image: {str(e)}")

    async def _extract_findings_from_content(
        self,
        content: str,
        source_doc_id: str,
        source_type: str,
        analysis_objective: str,
        metadata: Dict[str, Any]
    ) -> List[Finding]:
        system_prompt = (
            "You are a Document Analysis Agent. Your task is to extract specific, verifiable "
            "claims and data points from the provided document content that are relevant to the "
            "research objective. \n\n"
            "For each finding, identify:\n"
            " - claim: The factual statement or data point\n"
            " - excerpt: The raw text supporting this claim\n"
            " - confidence: high, medium, or low based on clarity and source reliability\n\n"
            "Return a JSON list of findings. Focus on:\n"
            " - Specific numbers, dates, and statistics\n"
            " - Named entities (people, companies, products)\n"
            " - Key claims and assertions\n"
            " - Relationships between entities"
        )

        truncated_content = content[:8000] if len(content) > 8000 else content

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Research Objective: {analysis_objective}\n\nDocument Content:\n{truncated_content}")
        ]

        try:
            response = await self.model.ainvoke(messages)
            return self._parse_findings_json(response.content, source_doc_id, source_type, metadata)
        except Exception as e:
            logger.error(f"Error extracting findings: {e}")
            return []

    def _parse_findings_json(
        self,
        json_str: str,
        source_doc_id: str,
        source_type: str,
        metadata: Dict[str, Any]
    ) -> List[Finding]:
        findings = []
        try:
            match = re.search(r'\[.*\]', json_str, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                for item in data:
                    confidence_str = item.get("confidence", "medium").lower()
                    confidence = Confidence.MEDIUM
                    if confidence_str == "high":
                        confidence = Confidence.HIGH
                    elif confidence_str == "low":
                        confidence = Confidence.LOW

                    finding = Finding(
                        id=f"finding_{uuid.uuid4().hex[:8]}",
                        claim=item.get("claim", ""),
                        source_doc_id=source_doc_id,
                        source_page=metadata.get("page"),
                        source_excerpt=item.get("excerpt", ""),
                        confidence=confidence,
                        metadata={
                            "source_type": source_type,
                            "filename": metadata.get("filename")
                        }
                    )
                    findings.append(finding)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error: {e}")
        except Exception as e:
            logger.warning(f"Error parsing findings: {e}")

        return findings

    def _extract_table_findings(self, research_obj: ResearchObject) -> List[Finding]:
        findings = []
        for elem in research_obj.elements:
            if elem.type == "table":
                finding = Finding(
                    id=f"finding_{uuid.uuid4().hex[:8]}",
                    claim=f"Table data from {research_obj.metadata.get('filename', 'document')}",
                    source_doc_id=research_obj.id,
                    source_excerpt=elem.content,
                    confidence=Confidence.HIGH,
                    metadata={
                        "source_type": "table",
                        "table_index": elem.metadata.get("table_index")
                    }
                )
                findings.append(finding)
        return findings

    def _error_result(self, error_message: str) -> DocumentAnalystResult:
        return {
            "findings": [],
            "research_objects": [],
            "analysis_summary": error_message,
        }

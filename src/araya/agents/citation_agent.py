import json
import re
import logging
from typing import Dict, List, Any

from araya.agents.state import ResearchState
from araya.agents.models import Finding
from araya.agents.lead_agent import get_model

logger = logging.getLogger(__name__)


class CitationAgent:
    def __init__(self):
        self.model = get_model("gemini-1.5-flash")

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        findings = state.get("findings", [])

        if not findings:
            return {"citation_map": {}}

        citation_map = self.build_citation_map(findings)
        return {"citation_map": citation_map}

    def build_citation_map(self, findings: List[Finding]) -> Dict[str, Dict[str, Any]]:
        citation_map = {}

        for finding in findings:
            source = finding.source_url or finding.source_doc_id or "unknown"
            citation_map[finding.id] = {
                "source": source,
                "claim": finding.claim,
                "excerpt": finding.source_excerpt,
                "credibility": finding.metadata.get("credibility_score", 0.5)
            }

        return citation_map

    def inject_citations(self, text: str, citation_map: Dict[str, Dict[str, Any]]) -> str:
        for finding_id, citation in citation_map.items():
            marker = f"[{finding_id}]"
            if marker in text:
                continue
            if citation["claim"] and citation["claim"][:50] in text:
                text = text.replace(
                    citation["claim"][:50],
                    f"{citation['claim'][:50]} [{finding_id}]",
                    1
                )
        return text

    def generate_footnotes(self, citation_map: Dict[str, Dict[str, Any]]) -> str:
        footnotes = []
        for finding_id, citation in citation_map.items():
            source = citation.get("source", "unknown")
            claim_preview = citation.get("claim", "")[:100]
            footnotes.append(f"[{finding_id}] {source} — {claim_preview}...")
        return "\n".join(footnotes)

    def _format_citation(self, citation: Dict[str, Any], style: str = "academic") -> str:
        if style == "academic":
            return f'[{citation["source"]}] {citation["claim"]}'
        return f'({citation["source"]}) {citation["claim"]}'

    def _format_citations(self, citation_map: Dict[str, Any]) -> List[str]:
        formatted = []
        for citation_id, citation in citation_map.items():
            formatted.append(self._format_citation(citation))
        return formatted

from typing import List, Dict, Any, Optional

from jinja2 import Template
from langchain_core.messages import HumanMessage, SystemMessage

from araya.agents.models import Finding
from araya.agents.lead_agent import get_model
from araya.agents.citation_agent import CitationAgent


class ReportEngine:
    def __init__(self):
        self.model = get_model("gemini-1.5-pro")
        self.citation_agent = CitationAgent()

    async def generate_report(self, objective: str, findings: List[Finding], template_str: Optional[str] = None) -> str:
        citation_map = self.citation_agent.build_citation_map(findings)

        sections = await self.synthesize_findings(objective, findings)

        annotated_sections = []
        for section in sections:
            content = section.get("content", "")
            annotated_content = self.citation_agent.inject_citations(content, citation_map)
            annotated_sections.append({
                "title": section.get("title"),
                "content": annotated_content
            })

        report_md = self._render_markdown(objective, annotated_sections, citation_map)

        return report_md

    async def synthesize_findings(self, objective: str, findings: List[Finding]) -> List[Dict[str, str]]:
        system_prompt = (
            "You are a Senior Research Analyst. Your goal is to synthesize research findings "
            "into a coherent, structured report. Group related findings into logical sections. "
            "Use markdown for formatting. For every claim you make, include the finding ID "
            "in brackets like [finding_id]."
        )

        findings_text = "\n".join(
            f"- [{f.id}] {f.claim} (Source: {f.source_url or f.source_doc_id or 'unknown'})"
            for f in findings
        )

        prompt = f"Objective: {objective}\n\nFindings:\n{findings_text}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ]

        response = await self.model.ainvoke(messages)

        return [{"title": "Analysis", "content": response.content}]

    def _render_markdown(self, objective: str, sections: List[Dict[str, str]], citation_map: Dict[str, Dict[str, Any]]) -> str:
        report = f"# Research Report: {objective}\n\n"

        for section in sections:
            if section["title"] != "Analysis":
                report += f"## {section['title']}\n\n"
            report += section["content"] + "\n\n"

        report += "## References\n\n"
        report += self.citation_agent.generate_footnotes(citation_map)

        return report

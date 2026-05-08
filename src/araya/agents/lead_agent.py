import json
import re
import logging
from typing import Dict, List, Any
from unittest.mock import AsyncMock

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from araya.agents.state import ResearchState
from araya.agents.models import Finding, ResearchPlanItem
from araya.core.config import settings

logger = logging.getLogger(__name__)


def get_model(model_name: str = "gemini-1.5-flash"):
    if not settings.GOOGLE_API_KEY:
        mock = AsyncMock()
        mock.ainvoke = AsyncMock(return_value=AIMessage(content='{"tasks": []}'))
        return mock
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
        timeout=settings.HTTP_REQUEST_TIMEOUT  # Apply timeout configuration
    )


class LeadResearchAgent:
    def __init__(self):
        self.model = get_model("gemini-1.5-pro")

    async def plan(self, state: ResearchState) -> Dict[str, Any]:
        objective = state.get("objective")
        findings = state.get("findings", [])
        existing_plan = state.get("plan", [])
        iteration = state.get("iteration_count", 0)

        existing_tasks = "\n".join(
            f"- [{p.task_id}] {p.description} (status: {p.status})"
            for p in existing_plan
        ) if existing_plan else "None"

        findings_summary = "\n".join(
            f"- [{f.id}] {f.claim} (source: {f.source_id})"
            for f in findings
        ) if findings else "None yet"

        system_prompt = (
            "You are the Lead Research Agent at Araya Labs. "
            "Your goal is to coordinate a team of specialist agents to perform deep research. "
            "Based on the objective, create a structured research plan as a JSON list of tasks. "
            "Each task should have a 'task_id' (string) and 'description' (string). "
            "If findings are already present, update the plan to address missing information. "
            "If this is a refinement iteration, focus on gaps identified in the evaluation feedback. "
            "Return ONLY a JSON object with a 'tasks' key containing the list."
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=(
                f"Objective: {objective}\n"
                f"Iteration: {iteration}\n"
                f"Existing Plan:\n{existing_tasks}\n"
                f"Current Findings:\n{findings_summary}\n"
                f"Evaluation Feedback: {state.get('evaluation', {}).get('feedback', 'N/A') if state.get('evaluation') else 'N/A'}"
            ))
        ]

        response = await self.model.ainvoke(messages)

        plan_items = self._parse_plan(response.content)
        
        # Validate that we got meaningful results
        if not plan_items:
            logger.warning("LeadAgent generated empty plan, creating fallback task")
            plan_items = [ResearchPlanItem(
                task_id="fallback_task",
                description=f"Research objective: {objective}",
                status="pending"
            )]

        return {
            "plan": plan_items,
        }

    async def synthesize(self, state: ResearchState) -> Dict[str, Any]:
        objective = state.get("objective")
        findings = state.get("findings", [])
        plan = state.get("plan", [])

        findings_text = "\n".join(
            f"- [{f.id}] {f.claim} (Source: {f.source_url or f.source_doc_id or 'unknown'})"
            for f in findings
        )
        plan_text = "\n".join(
            f"- {p.description} (Status: {p.status})"
            for p in plan
        )

        system_prompt = (
            "You are a Senior Research Analyst at Araya Labs. Your task is to synthesize "
            "the research findings into a comprehensive, well-structured report in Markdown. "
            "For every factual claim, reference the finding ID in brackets like [finding_id]. "
            "Structure the report with:\n"
            "1. Executive Summary\n"
            "2. Detailed Findings (grouped by theme)\n"
            "3. Contradictions & Nuances\n"
            "4. Source Appendix\n"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=(
                f"Research Objective: {objective}\n\n"
                f"Research Plan:\n{plan_text}\n\n"
                f"Findings:\n{findings_text}"
            ))
        ]

        response = await self.model.ainvoke(messages)

        return {
            "report": response.content,
        }

    def _parse_plan(self, content: str) -> List[ResearchPlanItem]:
        try:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                tasks = data.get("tasks", [])
                return [
                    ResearchPlanItem(
                        task_id=t.get("task_id", f"task_{i}"),
                        description=t.get("description", ""),
                        status="pending"
                    )
                    for i, t in enumerate(tasks)
                ]
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse plan JSON: {e}")

        lines = [line.strip().lstrip("- ").strip() for line in content.split("\n") if line.strip()]
        return [
            ResearchPlanItem(task_id=f"task_{i}", description=desc, status="pending")
            for i, desc in enumerate(lines) if desc
        ]

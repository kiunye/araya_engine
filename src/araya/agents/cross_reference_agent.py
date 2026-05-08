import json
import re
import logging
from typing import List, Dict, Any

from pydantic import BaseModel, Field

from araya.agents.state import ResearchState
from araya.agents.models import Finding, ResearchPlanItem
from araya.agents.lead_agent import get_model

logger = logging.getLogger(__name__)


class CrossRefAnalysis(BaseModel):
    corroborations: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    suggested_tasks: List[str] = Field(default_factory=list)


class CrossReferenceAgent:
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.llm = get_model(model_name)

    async def analyze(self, state: ResearchState) -> Dict[str, Any]:
        findings = state.get('findings', [])

        findings_str = "\n".join(
            f"ID: {f.id} | Claim: {f.claim} (Source: {f.source_id})"
            for f in findings
        )

        prompt = (
            f"You are a Logic and Verification Agent. Your goal is to analyze the research findings "
            f"for cross-source consistency.\n\n"
            f"RESEARCH OBJECTIVE: {state.get('objective')}\n\n"
            f"FINDINGS:\n{findings_str}\n\n"
            f"Task:\n"
            f"1. Identify Corroborations: Where multiple sources agree on a fact.\n"
            f"2. Identify Contradictions: Where sources provide conflicting data.\n"
            f"3. Identify Gaps: What parts of the Research Objective remain unanswered?\n"
            f"4. Suggest Tasks: If there are gaps or contradictions, what specific search query "
            f"or document analysis should be done next?\n\n"
            f"Provide your analysis in JSON format with keys: "
            f"corroborations, contradictions, gaps, suggested_tasks. "
            f"Each should be a list of strings."
        )

        try:
            from langchain_core.messages import HumanMessage
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                analysis = CrossRefAnalysis(**data)

                new_tasks = [
                    ResearchPlanItem(
                        task_id=f"gap_{i}",
                        description=task,
                        status="pending"
                    )
                    for i, task in enumerate(analysis.suggested_tasks)
                ]

                return {
                    "plan": new_tasks,
                    "errors": analysis.contradictions
                }

            raise ValueError("No JSON found in response")
        except Exception as e:
            logger.error(f"Cross-reference analysis failed: {e}")
            return {"errors": [f"Cross-reference error: {str(e)}"]}


async def run_cross_reference(state: ResearchState) -> Dict[str, Any]:
    agent = CrossReferenceAgent()
    logger.info("Running cross-reference analysis...")
    return await agent.analyze(state)

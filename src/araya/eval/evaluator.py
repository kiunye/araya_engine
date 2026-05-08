import json
import re
import logging
from typing import Dict, Any

from araya.agents.state import ResearchState
from araya.agents.models import EvaluationScore
from araya.agents.lead_agent import get_model

logger = logging.getLogger(__name__)


class Evaluator:
    def __init__(self, model_name: str = "gemini-1.5-pro", threshold: float = 7.0):
        self.llm = get_model(model_name)
        self.threshold = threshold

    async def evaluate_report(self, state: ResearchState) -> EvaluationScore:
        findings = state.get('findings', [])
        plan = state.get('plan', [])

        findings_context = "\n".join(
            f"[{f.id}] {f.claim} (Source: {f.source_url or f.source_doc_id or 'unknown'})"
            for f in findings
        )
        plan_context = "\n".join(
            f"- {p.description} (Status: {p.status})"
            for p in plan
        )

        prompt = (
            f"You are an expert Research Quality Auditor.\n"
            f"Evaluate the following research report based on the provided Findings and the original Research Plan.\n\n"
            f"ORIGINAL OBJECTIVE: {state.get('objective')}\n\n"
            f"RESEARCH PLAN:\n{plan_context}\n\n"
            f"FINDINGS COLLECTED:\n{findings_context}\n\n"
            f"RESEARCH REPORT:\n{state.get('report', '')}\n\n"
            f"Your task:\n"
            f"1. Grounding: Verify if every claim in the report is directly supported by the 'Findings Collected'.\n"
            f"2. Completeness: Check if the report addresses all items in the 'Research Plan' and the 'Original Objective'.\n\n"
            f"Output your evaluation in strict JSON format with the following keys:\n"
            f"- grounding_score (0-10)\n"
            f"- completeness_score (0-10)\n"
            f"- feedback (string)\n"
            f"- passed (boolean)\n\n"
            f"A report passes if both scores are >= {self.threshold}."
        )

        try:
            from langchain_core.messages import HumanMessage
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return EvaluationScore(
                    grounding_score=data['grounding_score'],
                    completeness_score=data['completeness_score'],
                    feedback=data['feedback'],
                    passed=data['passed']
                )
            raise ValueError("No JSON found in response")
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return EvaluationScore(
                grounding_score=0,
                completeness_score=0,
                feedback=f"Evaluation engine error: {str(e)}",
                passed=False
            )


async def run_evaluation_loop(state: ResearchState) -> Dict[str, Any]:
    evaluator = Evaluator()
    logger.info("Starting report evaluation loop...")

    score = await evaluator.evaluate_report(state)

    return {
        "evaluation": score,
        "iteration_count": state.get("iteration_count", 0) + 1
    }

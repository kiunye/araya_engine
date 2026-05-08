from typing import List, TypedDict, Annotated
import operator
from .models import Finding, ResearchPlanItem, EvaluationScore


def merge_findings(left: List[Finding], right: List[Finding]) -> List[Finding]:
    return left + right


def merge_plans(left: List[ResearchPlanItem], right: List[ResearchPlanItem]) -> List[ResearchPlanItem]:
    existing_ids = {item.task_id for item in left}
    new_items = [item for item in right if item.task_id not in existing_ids]
    return left + new_items


class ResearchState(TypedDict):
    objective: str
    plan: Annotated[List[ResearchPlanItem], merge_plans]
    findings: Annotated[List[Finding], merge_findings]
    report: str
    evaluation: EvaluationScore
    iteration_count: int
    errors: Annotated[List[str], operator.add]

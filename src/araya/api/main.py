import uuid
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from araya.core.config import settings
from araya.agents.orchestrator import research_engine

import logging
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Araya Engine",
    openapi_url="/openapi.json"
)


class ResearchRequest(BaseModel):
    objective: str = Field(..., description="The main research objective or question")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context or constraints")
    files: Optional[List[str]] = Field(default_factory=list, description="List of file paths to analyze")


class ResearchStatusResponse(BaseModel):
    research_id: str
    status: str
    created_at: str
    updated_at: Optional[str] = None
    error: Optional[str] = None


class ResearchReportResponse(BaseModel):
    research_id: str
    objective: str
    report: Optional[str] = None
    metadata: Dict[str, Any]


jobs: Dict[str, Dict[str, Any]] = {}


@app.get("/")
async def root():
    return {"message": "Welcome to Araya Engine API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/research/start", response_model=Dict[str, str])
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    research_id = str(uuid.uuid4())
    jobs[research_id] = {
        "status": "in-progress",
        "objective": request.objective,
        "files": request.files or [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "state": None,
        "error": None
    }

    background_tasks.add_task(
        run_research_task,
        research_id,
        request.objective,
        request.files or [],
        request.context
    )

    return {"research_id": research_id}


@app.get("/research/{research_id}/status", response_model=ResearchStatusResponse)
async def get_status(research_id: str):
    job = jobs.get(research_id)
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")

    return {
        "research_id": research_id,
        "status": job["status"],
        "created_at": job["created_at"],
        "updated_at": job.get("updated_at"),
        "error": job.get("error")
    }


@app.get("/research/{research_id}/report", response_model=ResearchReportResponse)
async def get_report(research_id: str):
    job = jobs.get(research_id)
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")

    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail=f"Research is still {job['status']}")

    state = job["state"]
    return {
        "research_id": research_id,
        "objective": job["objective"],
        "report": state.get("report") if state else None,
        "metadata": {}
    }


@app.get("/research/{research_id}/findings")
async def get_findings(research_id: str):
    job = jobs.get(research_id)
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")

    state = job.get("state")
    if not state:
        return {"findings": [], "status": job["status"]}

    findings = state.get("findings", [])
    serializable_findings = []
    for f in findings:
        if hasattr(f, "model_dump"):
            serializable_findings.append(f.model_dump())
        elif isinstance(f, dict):
            serializable_findings.append(f)
        else:
            serializable_findings.append(str(f))

    return {
        "research_id": research_id,
        "findings": serializable_findings,
        "iteration_count": state.get("iteration_count", 0)
    }


async def run_research_task(
    research_id: str,
    objective: str,
    files: List[str],
    query_context: Optional[Dict[str, Any]]
):
    initial_state = {
        "objective": objective,
        "plan": [],
        "findings": [],
        "report": "",
        "evaluation": None,
        "iteration_count": 0,
        "errors": [],
    }

    if files:
        initial_state["files"] = files

    try:
        final_state = await research_engine.ainvoke(initial_state)

        jobs[research_id]["status"] = "complete"
        jobs[research_id]["state"] = final_state
        jobs[research_id]["updated_at"] = datetime.utcnow().isoformat()
    except Exception as e:
        import traceback
        logger.error(f"Research task failed: {e}")
        traceback.print_exc()
        jobs[research_id]["status"] = "failed"
        jobs[research_id]["error"] = str(e)
        jobs[research_id]["updated_at"] = datetime.utcnow().isoformat()

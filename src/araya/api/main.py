import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import re
import hashlib
from collections import defaultdict
import time

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Request, status
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from araya.core.config import settings
from araya.agents.orchestrator import research_engine

import logging
logger = logging.getLogger(__name__)

# Security: Rate limiting storage
request_counts = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # 1 minute window
RATE_LIMIT_MAX_REQUESTS = 10  # Max requests per window

# Security: API key validation (if we implement API key authentication)
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def check_rate_limit(request: Request):
    """Check if the request exceeds the rate limit."""
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old requests outside the window
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip]
        if current_time - req_time < RATE_LIMIT_WINDOW
    ]
    
    # Check if limit exceeded
    if len(request_counts[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    # Add current request
    request_counts[client_ip].append(current_time)

async def get_api_key(api_key_header: str = Depends(api_key_header)):
    """Validate API key if authentication is enabled."""
    # For now, we'll just log if an API key is provided
    # In a production environment, you would validate against a secure store
    if api_key_header:
        logger.info(f"API key provided: {api_key_header[:8]}...")
        # TODO: Implement actual API key validation against secure store
        # For now, we allow requests without API key for simplicity
        return api_key_header
    return None

app = FastAPI(
    title="Araya Engine",
    description="Multi-agent research engine for automated due diligence and research tasks.",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)


class ResearchRequest(BaseModel):
    objective: str = Field(..., description="The main research objective or question")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context or constraints")
    files: Optional[List[str]] = Field(default_factory=list, description="List of file paths to analyze")
    
    @validator('objective')
    def objective_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Objective must not be empty')
        return v.strip()
    
    @validator('objective')
    def objective_length_limit(cls, v):
        if len(v) > 500:
            raise ValueError('Objective must not exceed 500 characters')
        return v


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


# Scalability: In production, consider replacing this with a proper database (Redis, PostgreSQL, etc.)
# For now, we'll keep in-memory storage but add scalability improvements
jobs: Dict[str, Dict[str, Any]] = {}
JOB_CLEANUP_HOURS = 24  # Auto-clean jobs older than this
MAX_CONCURRENT_JOBS = 100  # Limit concurrent jobs to prevent resource exhaustion
JOB_TIMEOUT_HOURS = 6  # Maximum time a job can run before being cancelled

# Metrics for monitoring
job_metrics = {
    "total_started": 0,
    "total_completed": 0,
    "total_failed": 0,
    "total_cleaned_up": 0,
    "current_active": 0
}

def cleanup_old_jobs():
    """Remove old jobs to prevent memory leaks."""
    current_time = datetime.utcnow()
    cutoff_time = current_time - timedelta(hours=JOB_CLEANUP_HOURS)
    
    jobs_to_remove = []
    for research_id, job in jobs.items():
        created_at_str = job.get("created_at")
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str)
                if created_at < cutoff_time:
                    jobs_to_remove.append(research_id)
            except ValueError:
                # If we can't parse the date, remove the job to be safe
                jobs_to_remove.append(research_id)
    
    for research_id in jobs_to_remove:
        del jobs[research_id]
        job_metrics["total_cleaned_up"] += 1
        logger.info(f"Cleaned up old job: {research_id}")

def get_system_metrics():
    """Get current system metrics for monitoring."""
    return {
        **job_metrics,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - app_start_time if 'app_start_time' in globals() else 0
    }

# Track application start time for uptime metrics
app_start_time = time.time()

def update_job_status(research_id: str, status: str, **kwargs):
    """Update job status with metrics tracking."""
    if research_id in jobs:
        old_status = jobs[research_id].get("status")
        jobs[research_id]["status"] = status
        jobs[research_id]["updated_at"] = datetime.utcnow().isoformat()
        
        # Update metrics based on status changes
        if old_status != status:
            if status == "in-progress":
                job_metrics["total_started"] += 1
                job_metrics["current_active"] += 1
            elif status == "complete":
                job_metrics["total_completed"] += 1
                job_metrics["current_active"] -= 1
            elif status == "failed":
                job_metrics["total_failed"] += 1
                job_metrics["current_active"] -= 1
        
        # Update any additional fields
        for key, value in kwargs.items():
            jobs[research_id][key] = value

def can_start_new_job():
    """Check if we can start a new job based on resource limits."""
    return job_metrics["current_active"] < MAX_CONCURRENT_JOBS


@app.get("/")
async def root():
    return {"message": "Welcome to Araya Engine API", "version": "0.1.0"}


@app.get("/health")
async def health():
    # Perform periodic cleanup
    cleanup_old_jobs()
    return {"status": "healthy"}

@app.get("/metrics")
async def get_metrics():
    """Endpoint for monitoring metrics (could be used by Prometheus, etc.)."""
    return get_system_metrics()


@app.post("/research/start", response_model=Dict[str, str])
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks, _: None = Depends(check_rate_limit)):
    # Check if we can start a new job (scalability)
    if not can_start_new_job():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server is at maximum capacity. Please try again later."
        )
    
    # Input validation and sanitization (security)
    if not request.objective or not request.objective.strip():
        raise HTTPException(status_code=400, detail="Research objective cannot be empty")
    
    # Sanitize objective (basic HTML/script tag removal)
    objective = re.sub(r'<[^>]*>', '', request.objective.strip())
    if len(objective) > 500:  # Reasonable limit
        raise HTTPException(status_code=400, detail="Research objective too long (max 500 characters)")
    
    research_id = str(uuid.uuid4())
    # Use the new job management function
    update_job_status(
        research_id,
        "in-progress",
        objective=objective,
        files=request.files or [],
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        state=None,
        error=None
    )

    background_tasks.add_task(
        run_research_task,
        research_id,
        objective,
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
    # Initialize job tracking
    update_job_status(
        research_id,
        "in-progress",
        objective=objective,
        files=files or [],
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat()
    )

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
        # Add timeout for the entire research process
        final_state = await asyncio.wait_for(
            research_engine.ainvoke(initial_state),
            timeout=JOB_TIMEOUT_HOURS * 3600  # Convert hours to seconds
        )

        update_job_status(
            research_id,
            "complete",
            state=final_state,
            updated_at=datetime.utcnow().isoformat()
        )
    except asyncio.TimeoutError:
        logger.error(f"Research task {research_id} timed out after {JOB_TIMEOUT_HOURS} hours")
        update_job_status(
            research_id,
            "failed",
            error=f"Research timed out after {JOB_TIMEOUT_HOURS} hours",
            updated_at=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Research task failed: {e}")
        update_job_status(
            research_id,
            "failed",
            error=str(e),
            updated_at=datetime.utcnow().isoformat()
        )

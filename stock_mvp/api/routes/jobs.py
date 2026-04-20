from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.jobs import job_store


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateAnalysisJobBody(BaseModel):
    ai_enabled: bool = True
    refresh_realtime_only: bool = False
    enabled_sources: Optional[List[str]] = None


@router.post("/analysis")
def create_analysis_job(body: CreateAnalysisJobBody):
    job = job_store.create_analysis_job(
        ai_enabled=body.ai_enabled,
        refresh_realtime_only=body.refresh_realtime_only,
        enabled_sources=body.enabled_sources,
    )
    return {"task_id": job.task_id, "status": job.status}


@router.get("/{task_id}")
def get_job(task_id: str):
    job = job_store.get(task_id)
    if not job:
        raise HTTPException(status_code=404, detail="task not found")
    return {
        "task_id": job.task_id,
        "status": job.status,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error": job.error,
        "result_summary": job.result_summary,
    }


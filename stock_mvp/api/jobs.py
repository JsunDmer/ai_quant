from __future__ import annotations

import threading
import time
import uuid
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal

from pipeline import run_post_close_pipeline

JobStatus = Literal["queued", "running", "success", "failed"]


@dataclass
class Job:
    task_id: str
    status: JobStatus
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None


class InMemoryJobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: Dict[str, Job] = {}

    def create_analysis_job(
        self,
        *,
        ai_enabled: bool,
        refresh_realtime_only: bool,
        enabled_sources: Optional[list[str]] = None,
    ) -> Job:
        task_id = uuid.uuid4().hex
        job = Job(task_id=task_id, status="queued", created_at=time.time())
        with self._lock:
            self._jobs[task_id] = job

        # pytest 环境下避免后台线程跑 pipeline（会触发三方库在多线程下的 native 崩溃）
        if os.environ.get("PYTEST_CURRENT_TEST"):
            self._run_analysis_job(
                task_id=task_id,
                ai_enabled=ai_enabled,
                refresh_realtime_only=refresh_realtime_only,
                enabled_sources=enabled_sources,
            )
        else:
            t = threading.Thread(
                target=self._run_analysis_job,
                kwargs={
                    "task_id": task_id,
                    "ai_enabled": ai_enabled,
                    "refresh_realtime_only": refresh_realtime_only,
                    "enabled_sources": enabled_sources,
                },
                daemon=True,
            )
            t.start()
        return job

    def get(self, task_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(task_id)

    def _run_analysis_job(
        self,
        *,
        task_id: str,
        ai_enabled: bool,
        refresh_realtime_only: bool,
        enabled_sources: Optional[list[str]],
    ) -> None:
        with self._lock:
            job = self._jobs.get(task_id)
            if not job:
                return
            job.status = "running"
            job.started_at = time.time()

        try:
            result = run_post_close_pipeline(
                ai_enabled=ai_enabled,
                refresh_realtime_only=refresh_realtime_only,
                enabled_sources=enabled_sources,
            )
            summary = {
                "status": result.get("status"),
                "trade_date": result.get("trade_date"),
                "data_date": result.get("data_date"),
                "errors": result.get("errors", []),
            }
            with self._lock:
                job = self._jobs.get(task_id)
                if not job:
                    return
                job.status = "success"
                job.finished_at = time.time()
                job.result_summary = summary
        except Exception as e:
            with self._lock:
                job = self._jobs.get(task_id)
                if not job:
                    return
                job.status = "failed"
                job.finished_at = time.time()
                job.error = str(e)


job_store = InMemoryJobStore()


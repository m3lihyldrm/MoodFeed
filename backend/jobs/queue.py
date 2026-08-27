"""MoodFeed Background Job Queue Abstraction.

Provides an asynchronous job execution interface and in-memory testable worker
for source sync, feature extraction, export packaging, and deletion cleanup.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable


class JobQueueInterface:
    """Interface for background tasks."""

    def enqueue(self, job_name: str, payload: dict[str, Any]) -> str: ...
    def get_job_status(self, job_id: str) -> dict[str, Any] | None: ...


class InMemoryJobQueue(JobQueueInterface):
    """In-memory task runner with job status tracking and error handling."""

    def __init__(self) -> None:
        self.jobs: dict[str, dict[str, Any]] = {}
        self.handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register_handler(self, job_name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self.handlers[job_name] = handler

    def enqueue(self, job_name: str, payload: dict[str, Any]) -> str:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        self.jobs[job_id] = {
            "job_id": job_id,
            "job_name": job_name,
            "payload": payload,
            "status": "pending",
            "result": None,
            "error": None,
            "created_at": time.time(),
            "completed_at": None,
        }

        # If handler is registered, execute immediately or synchronously in dev
        handler = self.handlers.get(job_name)
        if handler:
            try:
                self.jobs[job_id]["status"] = "processing"
                result = handler(payload)
                self.jobs[job_id]["status"] = "completed"
                self.jobs[job_id]["result"] = result
                self.jobs[job_id]["completed_at"] = time.time()
            except Exception as e:
                self.jobs[job_id]["status"] = "failed"
                self.jobs[job_id]["error"] = str(e)
                self.jobs[job_id]["completed_at"] = time.time()

        return job_id

    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        return self.jobs.get(job_id)


# Global job queue instance
job_queue = InMemoryJobQueue()

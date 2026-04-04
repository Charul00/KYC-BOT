import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobService:
    """
    Lightweight async job tracker.
    Stores job state on disk so app restarts do not immediately lose all status.
    """

    def __init__(self):
        self.docs_dir = Path(settings.DOCUMENTS_DIR)
        self.jobs_path = self.docs_dir / ".jobs_registry.json"
        self._jobs: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.jobs_path.exists():
            try:
                self._jobs = json.loads(self.jobs_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load jobs registry: {e}")
                self._jobs = {}

    def _save(self):
        try:
            self.docs_dir.mkdir(parents=True, exist_ok=True)
            self.jobs_path.write_text(
                json.dumps(self._jobs, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Failed to save jobs registry: {e}")

    def create_job(self, filename: str, file_type: str, file_size_mb: float) -> dict:
        job_id = str(uuid.uuid4())[:12]
        job = {
            "job_id": job_id,
            "filename": filename,
            "file_type": file_type,
            "file_size_mb": round(file_size_mb, 2),
            "status": "queued",   # queued | processing | ready | failed
            "progress": 0,        # 0-100 real progress percentage
            "stage": "",          # human-readable current stage label
            "message": "Job created",
            "chunks_created": 0,
            "created_at": _utcnow_iso(),
            "updated_at": _utcnow_iso(),
        }
        self._jobs[job_id] = job
        self._save()
        return job

    def update_job(self, job_id: str, **updates):
        if job_id not in self._jobs:
            return

        self._jobs[job_id].update(updates)
        self._jobs[job_id]["updated_at"] = _utcnow_iso()
        self._save()

    def get_job(self, job_id: str) -> Optional[dict]:
        return self._jobs.get(job_id)

    def list_jobs(self):
        return list(self._jobs.values())


job_service = JobService()
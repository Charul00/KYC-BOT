import logging
from pathlib import Path

from app.services.document_service import document_service
from app.services.job_service import job_service

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Background ingestion coordinator.
    """

    def process_job(self, job_id: str, file_path_str: str):
        file_path = Path(file_path_str)

        if not file_path.exists():
            job_service.update_job(
                job_id,
                status="failed",
                message="Uploaded file not found on disk.",
            )
            return

        try:
            job_service.update_job(
                job_id,
                status="processing",
                progress=2,
                stage="Starting…",
                message="Document processing started.",
            )

            # Progress callback — called by document_service at key stages.
            def _progress(pct: int, stage: str = "", message: str = ""):
                job_service.update_job(
                    job_id,
                    progress=min(int(pct), 98),
                    stage=stage,
                    message=message or stage,
                )

            result = document_service.process_saved_file(file_path, progress_callback=_progress)

            job_service.update_job(
                job_id,
                status="ready",
                progress=100,
                stage="Done",
                message="Document processed successfully.",
                chunks_created=result.get("chunks_created", 0),
            )

            logger.info(f"Async ingestion complete for job {job_id} | file={file_path.name}")

        except Exception as e:
            logger.error(f"Async ingestion failed for job {job_id}: {e}")
            job_service.update_job(
                job_id,
                status="failed",
                message=str(e),
            )


ingestion_service = IngestionService()
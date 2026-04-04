import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

import pandas as pd

from app.config import settings
from app.services.excel_service import excel_query_service

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class FileRegistryService:
    """
    Keeps lightweight metadata about uploaded files so the system
    can reason about available sources more intelligently.
    """

    def __init__(self):
        self.docs_dir = Path(settings.DOCUMENTS_DIR)
        self.registry_path = self.docs_dir / ".file_registry.json"
        self._registry: Dict[str, dict] = {}
        self._load_registry()

    def _load_registry(self):
        if self.registry_path.exists():
            try:
                self._registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load file registry: {e}")
                self._registry = {}

    def _save_registry(self):
        try:
            self.docs_dir.mkdir(parents=True, exist_ok=True)
            self.registry_path.write_text(
                json.dumps(self._registry, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Failed to save file registry: {e}")

    def _guess_file_role(self, filename: str, file_type: str, extracted_text: str = "") -> str:
        text = (filename + " " + extracted_text[:2000]).lower()

        if file_type == ".xlsx":
            return "structured_data"

        if file_type == ".pptx":
            if any(k in text for k in ["brd", "process", "rules", "policy", "review", "escalation"]):
                return "process_document"
            if any(k in text for k in ["customer", "kyc", "onboarding", "risk", "profile"]):
                return "kyc_document"
            return "presentation_document"

        if file_type in [".png", ".jpg", ".jpeg"]:
            if any(k in text for k in ["brd", "process", "rules", "policy", "review", "escalation"]):
                return "process_document"
            if any(k in text for k in ["customer", "kyc", "id", "address", "risk", "profile"]):
                return "kyc_document"
            return "image_document"

        if any(k in text for k in ["brd", "process", "rules", "policy", "guideline", "review rules", "escalation"]):
            return "process_document"

        if any(k in text for k in ["customer", "kyc", "onboarding", "risk", "profile"]):
            return "kyc_document"

        return "generic_document"

    def _extract_excel_summary(self, file_path: Path) -> dict:
        summary = {
            "sheet_names": [],
            "row_count": 0,
            "column_names": [],
        }
        try:
            workbook = pd.read_excel(file_path, sheet_name=None)
            all_columns = []
            total_rows = 0
            for sheet_name, df in workbook.items():
                summary["sheet_names"].append(sheet_name)
                if df is not None:
                    total_rows += len(df)
                    all_columns.extend([str(c).strip() for c in df.columns])
            summary["row_count"] = total_rows
            summary["column_names"] = list(dict.fromkeys(all_columns))
        except Exception as e:
            logger.warning(f"Excel summary extraction failed for {file_path.name}: {e}")
        return summary

    def upsert_file(
        self,
        filename: str,
        file_type: str,
        file_size_mb: float,
        extracted_text: str = "",
    ):
        file_path = self.docs_dir / filename
        role = self._guess_file_role(filename, file_type, extracted_text)

        entry = {
            "filename": filename,
            "file_type": file_type,
            "file_size_mb": round(file_size_mb, 2),
            "uploaded_at": _utcnow_iso(),
            "role": role,
        }

        if file_type == ".xlsx":
            entry["excel_summary"] = self._extract_excel_summary(file_path)

        self._registry[filename] = entry
        self._save_registry()
        logger.info(f"File registry updated for {filename}")

    def remove_file(self, filename: str):
        if filename in self._registry:
            del self._registry[filename]
            self._save_registry()

    def list_files(self) -> List[dict]:
        return list(self._registry.values())

    def get_file(self, filename: str) -> Optional[dict]:
        return self._registry.get(filename)

    def get_source_summary(self) -> str:
        if not self._registry:
            return "No uploaded source metadata available."

        role_counts: Dict[str, int] = {}
        file_types: Dict[str, int] = {}
        for item in self._registry.values():
            role = item.get("role", "unknown")
            ftype = item.get("file_type", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1
            file_types[ftype] = file_types.get(ftype, 0) + 1

        role_text = ", ".join(f"{k}: {v}" for k, v in sorted(role_counts.items()))
        type_text = ", ".join(f"{k}: {v}" for k, v in sorted(file_types.items()))

        return f"Uploaded source roles -> {role_text}. File types -> {type_text}."

    def has_structured_data(self) -> bool:
        return any(item.get("role") == "structured_data" for item in self._registry.values())

    def has_process_document(self) -> bool:
        return any(item.get("role") == "process_document" for item in self._registry.values())


file_registry_service = FileRegistryService()
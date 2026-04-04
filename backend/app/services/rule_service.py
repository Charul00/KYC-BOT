import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
from langchain_openai import ChatOpenAI

from app.config import settings
from app.prompts.rule_prompts import (
    RULE_EXTRACTION_PROMPT,
    RULE_EXPLANATION_PROMPT,
)
from app.services.excel_service import excel_query_service

logger = logging.getLogger(__name__)


class RuleExecutionService:
    """
    Extracts simple BRD/process rules from uploaded document text
    and applies them to structured Excel data.
    """

    def __init__(self):
        self.docs_dir = Path(settings.DOCUMENTS_DIR)
        self._llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.0,
            max_tokens=1200,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self._rules_cache: List[dict] = []

    # =========================
    # Rule source loading
    # =========================

    def refresh_rules(self):
        text = self._load_rule_source_text()
        if not text.strip():
            self._rules_cache = []
            logger.info("Rule cache cleared: no BRD/process text found.")
            return

        try:
            self._rules_cache = self._extract_rules(text)
            logger.info(f"Loaded {len(self._rules_cache)} rule(s) from document sources.")
        except Exception as e:
            logger.warning(f"Rule extraction failed: {e}")
            self._rules_cache = []

    def _load_rule_source_text(self) -> str:
        """
        For Phase 1.5:
        Read all text-like files already uploaded in DOCUMENTS_DIR.
        We use them as BRD/process context.
        """
        parts = []
        if not self.docs_dir.exists():
            return ""

        for file_path in self.docs_dir.iterdir():
            ext = file_path.suffix.lower()

            try:
                if ext in [".txt", ".md"]:
                    parts.append(file_path.read_text(encoding="utf-8"))

                elif ext == ".pdf":
                    from pypdf import PdfReader
                    reader = PdfReader(str(file_path))
                    text = "\n".join(page.extract_text() or "" for page in reader.pages)
                    parts.append(text)

                elif ext == ".docx":
                    import zipfile
                    import xml.etree.ElementTree as ET

                    text_parts = []
                    with zipfile.ZipFile(str(file_path)) as z:
                        with z.open("word/document.xml") as f:
                            tree = ET.parse(f)
                            root = tree.getroot()
                            for t_elem in root.iter(
                                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
                            ):
                                if t_elem.text:
                                    text_parts.append(t_elem.text)
                    parts.append(" ".join(text_parts))
            except Exception as e:
                logger.warning(f"Failed to read rule source from {file_path.name}: {e}")

        return "\n\n".join(parts)

    def _extract_rules(self, text: str) -> List[dict]:
        prompt = RULE_EXTRACTION_PROMPT + "\n\n" + text[:12000]
        response = self._llm.invoke(prompt)
        parsed = json.loads(response.content.strip())
        return parsed.get("rules", [])

    # =========================
    # Routing
    # =========================

    def is_rule_query(self, query: str) -> bool:
        q = query.lower()

        patterns = [
            "based on brd",
            "based on the brd",
            "based on process",
            "based on rules",
            "according to the rule",
            "according to the rules",
            "which customers need review",
            "who should be reviewed",
            "who should be prioritized",
            "which cases require review",
            "which cases need escalation",
            "which customers need monitoring",
            "which records match the rule",
            "apply the rule",
        ]
        return any(p in q for p in patterns)

    # =========================
    # Semantic mapping
    # =========================

    def _find_best_df(self) -> Optional[pd.DataFrame]:
        if not excel_query_service._cache:
            excel_query_service.refresh()

        if not excel_query_service._cache:
            return None

        key = max(excel_query_service._cache.keys(), key=lambda k: len(excel_query_service._cache[k]))
        return excel_query_service._cache[key].copy()

    def _build_semantic_map(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Map semantic hints to actual columns as best effort.
        """
        columns = list(df.columns)
        lower_map = {c.lower(): c for c in columns}

        semantic_map = {}

        aliases = {
            "customer_id": ["customer id", "member id", "client id", "cust id", "id"],
            "name": ["name", "customer name", "client name", "member name"],
            "risk": ["risk flag", "risk level", "risk category", "risk"],
            "duration": [
                "onboarding duration",
                "onboarding duration (mins)",
                "tat",
                "processing time",
                "turnaround time",
                "onboarding time",
                "duration",
            ],
            "profile_type": ["profile type", "customer type", "member type"],
            "location": ["location", "city", "branch location"],
            "occupation": ["occupation", "profession", "job"],
            "channel": ["onboarding channel", "channel"],
        }

        for semantic_key, hints in aliases.items():
            for hint in hints:
                for col in columns:
                    if hint in col.lower():
                        semantic_map[semantic_key] = col
                        break
                if semantic_key in semantic_map:
                    break

        return semantic_map

    def _resolve_field_hint(self, field_hint: str, semantic_map: Dict[str, str]) -> Optional[str]:
        hint = field_hint.lower().strip()

        if "duration" in hint or "onboarding" in hint or "tat" in hint:
            return semantic_map.get("duration")
        if "risk" in hint:
            return semantic_map.get("risk")
        if "customer" in hint and "id" in hint:
            return semantic_map.get("customer_id")
        if "name" in hint:
            return semantic_map.get("name")
        if "profile" in hint or "type" in hint:
            return semantic_map.get("profile_type")
        if "location" in hint or "city" in hint:
            return semantic_map.get("location")
        if "occupation" in hint or "profession" in hint:
            return semantic_map.get("occupation")
        if "channel" in hint:
            return semantic_map.get("channel")

        return None

    # =========================
    # Execution
    # =========================

    def _apply_condition(self, df: pd.DataFrame, column: str, operator: str, value: Any) -> pd.DataFrame:
        result = df.copy()
        series = result[column]

        if operator in {"gt", "gte", "lt", "lte"}:
            numeric_series = pd.to_numeric(series, errors="coerce")
            numeric_value = float(value)

            if operator == "gt":
                return result[numeric_series > numeric_value]
            if operator == "gte":
                return result[numeric_series >= numeric_value]
            if operator == "lt":
                return result[numeric_series < numeric_value]
            if operator == "lte":
                return result[numeric_series <= numeric_value]

        if operator == "equals":
            return result[series.astype(str).str.lower() == str(value).lower()]

        if operator == "contains":
            return result[series.astype(str).str.lower().str.contains(str(value).lower(), na=False)]

        return result

    def _execute_rules(self, df: pd.DataFrame, rules: List[dict]) -> List[dict]:
        semantic_map = self._build_semantic_map(df)
        results = []

        for rule in rules:
            working = df.copy()
            applied_conditions = []

            for condition in rule.get("conditions", []):
                field_hint = condition.get("field_hint", "")
                operator = condition.get("operator", "")
                value = condition.get("value")

                actual_column = self._resolve_field_hint(field_hint, semantic_map)
                if not actual_column or actual_column not in working.columns:
                    continue

                working = self._apply_condition(working, actual_column, operator, value)
                applied_conditions.append({
                    "field_hint": field_hint,
                    "actual_column": actual_column,
                    "operator": operator,
                    "value": value,
                })

            if not applied_conditions:
                continue

            results.append({
                "rule_id": rule.get("rule_id"),
                "description": rule.get("description"),
                "action": rule.get("action"),
                "priority": rule.get("priority"),
                "matched_count": int(len(working)),
                "applied_conditions": applied_conditions,
                "rows": working.head(20).fillna("").to_dict(orient="records"),
            })

        return results

    def _compose_answer(self, query: str, execution_results: List[dict]) -> str:
        prompt = (
            RULE_EXPLANATION_PROMPT
            + "\n\n"
            + f"User question: {query}\n"
            + f"Executed rules and matches: {json.dumps(execution_results, ensure_ascii=False)}"
        )
        response = self._llm.invoke(prompt)
        return response.content.strip()

    # =========================
    # Public API
    # =========================

    def answer_query(self, query: str) -> str:
        if not self._rules_cache:
            self.refresh_rules()

        if not self._rules_cache:
            return (
                "I couldn't find any explicit BRD or process rules in the uploaded documents "
                "to execute against the spreadsheet data."
            )

        df = self._find_best_df()
        if df is None or df.empty:
            return "I couldn't find any uploaded Excel data to apply the rules to."

        try:
            results = self._execute_rules(df, self._rules_cache)
            if not results:
                return (
                    "I found uploaded rules and spreadsheet data, but I could not map those rules "
                    "reliably to the current spreadsheet structure."
                )

            return self._compose_answer(query, results)
        except Exception as e:
            logger.error(f"Rule execution failed: {e}")
            return "I encountered an error while applying the uploaded rules to the spreadsheet data."


rule_execution_service = RuleExecutionService()
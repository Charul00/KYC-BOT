import json
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any

import pandas as pd
from langchain_openai import ChatOpenAI

from app.config import settings
from app.prompts.excel_prompts import (
    EXCEL_SCHEMA_PROMPT,
    EXCEL_QUERY_PLAN_PROMPT,
    EXCEL_FOLLOWUP_PROMPT,
    EXCEL_ANSWER_PROMPT,
)

logger = logging.getLogger(__name__)


class ExcelQueryService:
    """
    Intelligent Excel query engine.

    Flow:
    1. Load workbook sheets
    2. Infer schema with LLM (includes sample categorical values)
    3. Resolve follow-up dynamically
    4. Plan query with LLM (sheet selection + intent)
    5. Execute deterministically with pandas
    6. Compose natural answer with LLM
    """

    def __init__(self):
        self.docs_dir = Path(settings.DOCUMENTS_DIR)
        self._cache: Dict[str, pd.DataFrame] = {}
        self._schema_cache: Dict[str, dict] = {}
        self._llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.0,
            max_tokens=1500,
            openai_api_key=settings.OPENAI_API_KEY,
        )

    # =========================
    # Loading / Refresh
    # =========================

    def refresh(self):
        self._cache = self._load_all_excel_data()
        self._schema_cache = {}
        for key, df in self._cache.items():
            try:
                self._schema_cache[key] = self._infer_schema_for_df(key, df)
            except Exception as e:
                logger.warning(f"Schema inference failed for {key}: {e}")
        logger.info(
            f"Excel cache refreshed with {len(self._cache)} sheet(s), "
            f"{len(self._schema_cache)} schema profile(s)."
        )

    def _load_all_excel_data(self) -> Dict[str, pd.DataFrame]:
        excel_data: Dict[str, pd.DataFrame] = {}

        if not self.docs_dir.exists():
            return excel_data

        for file_path in self.docs_dir.iterdir():
            if file_path.suffix.lower() == ".xlsx":
                try:
                    workbook = pd.read_excel(file_path, sheet_name=None)
                    for sheet_name, df in workbook.items():
                        if df is not None and not df.empty:
                            key = f"{file_path.name}::{sheet_name}"
                            excel_data[key] = self._normalize_df(df)
                except Exception as e:
                    logger.warning(f"Failed to load Excel file {file_path.name}: {e}")

        return excel_data

    def _normalize_df(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]
        return df

    def _find_best_df_key(self) -> Optional[str]:
        if not self._cache:
            return None
        return max(self._cache.keys(), key=lambda k: len(self._cache[k]))

    def _get_best_df(self) -> Optional[pd.DataFrame]:
        key = self._find_best_df_key()
        return self._cache.get(key) if key else None

    # =========================
    # Query Routing Hint
    # =========================

    def is_excel_query(self, query: str) -> bool:
        q = query.lower()
        patterns = [
            "how many",
            "count",
            "highest",
            "lowest",
            "average",
            "avg",
            "maximum",
            "minimum",
            "list",
            "show",
            "which customers",
            "which members",
            "customers with",
            "members with",
            "compare",
            "greater than",
            "less than",
            ">",
            "<",
            "risk",
            "duration",
            "tat",
            "processing time",
            "turnaround",
            "onboarding time",
            "onboarding duration",
            "cust-",
        ]
        return any(p in q for p in patterns)

    # =========================
    # Schema Understanding
    # =========================

    def _get_categorical_sample_values(self, df: pd.DataFrame, max_cols: int = 20) -> dict:
        """
        For each column with few unique values (categorical-like), collect the
        distinct values so the LLM can use the exact correct filter values.
        """
        sample_values = {}
        for col in df.columns[:max_cols]:
            try:
                n_unique = df[col].nunique(dropna=True)
                # Only for low-cardinality (categorical) columns
                if 1 < n_unique <= 30:
                    vals = df[col].dropna().unique().tolist()
                    # Convert to string safely
                    sample_values[col] = [str(v) for v in vals[:30]]
            except Exception:
                pass
        return sample_values

    def _infer_schema_for_df(self, key: str, df: pd.DataFrame) -> dict:
        sample_rows = df.head(5).fillna("").to_dict(orient="records")
        sheet_name = key.split("::", 1)[1] if "::" in key else key
        categorical_values = self._get_categorical_sample_values(df)

        prompt = (
            EXCEL_SCHEMA_PROMPT
            + "\n\n"
            + f"Sheet name: {sheet_name}\n"
            + f"Columns: {list(df.columns)}\n"
            + f"Sample rows: {json.dumps(sample_rows, ensure_ascii=False)}"
        )

        try:
            response = self._llm.invoke(prompt)
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```", 2)[-1].lstrip("json").strip().rstrip("```").strip()
            result = json.loads(raw)
        except Exception as e:
            logger.warning(f"Schema LLM parse failed: {e}")
            result = {"sheet_purpose": sheet_name, "columns": []}

        # Attach categorical sample values directly to the schema
        result["sample_values"] = categorical_values
        return result

    def _get_schema_summary(self) -> dict:
        summary = {"sheets": []}
        for key, df in self._cache.items():
            schema = self._schema_cache.get(key, {})
            summary["sheets"].append(
                {
                    "sheet_key": key,
                    "row_count": len(df),
                    "columns": schema.get("columns", []),
                    "sheet_purpose": schema.get("sheet_purpose", ""),
                    "sample_values": schema.get("sample_values", {}),
                }
            )
        return summary

    # =========================
    # Follow-up Resolution
    # =========================

    def _resolve_followup(self, query: str, session_id: str = "default", memory_service=None) -> dict:
        if memory_service is None:
            return {"mode": "new_excel_query", "resolved_query": query}

        last_excel_query = memory_service.get_structured_state(session_id, "last_excel_query", "")
        last_excel_result = memory_service.get_structured_state(session_id, "last_excel_result", None)

        result_summary = "No previous Excel result."
        if last_excel_result:
            result_summary = json.dumps({
                "intent": last_excel_result.get("intent"),
                "row_count": last_excel_result.get("row_count", 0),
                "columns": last_excel_result.get("columns", []),
            }, ensure_ascii=False)

        prompt = (
            EXCEL_FOLLOWUP_PROMPT
            + "\n\n"
            + f"Current question: {query}\n"
            + f"Previous Excel query: {last_excel_query}\n"
            + f"Previous Excel result summary: {result_summary}"
        )

        try:
            response = self._llm.invoke(prompt)
            parsed = json.loads(response.content.strip())
            if parsed.get("mode") in {"reuse_last_result", "new_excel_query", "not_excel_followup"}:
                return parsed
        except Exception as e:
            logger.warning(f"Excel follow-up resolution failed: {e}")

        return {"mode": "new_excel_query", "resolved_query": query}

    # =========================
    # Query Planning
    # =========================

    def _plan_query(self, query: str) -> dict:
        schema_summary = self._get_schema_summary()
        prompt = (
            EXCEL_QUERY_PLAN_PROMPT
            + "\n\n"
            + f"User query: {query}\n"
            + f"Spreadsheet schema: {json.dumps(schema_summary, ensure_ascii=False)}"
        )

        response = self._llm.invoke(prompt)
        try:
            raw = response.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```", 2)[-1].lstrip("json").strip()
                if raw.endswith("```"):
                    raw = raw[:-3].strip()
            plan = json.loads(raw)
            if isinstance(plan, dict):
                logger.info(
                    f"Excel plan: intent={plan.get('intent')} sheet={plan.get('sheet_key')} "
                    f"filters={plan.get('filters')} agg={plan.get('aggregation')}"
                )
                return plan
        except Exception as e:
            logger.warning(f"Excel plan JSON parse failed: {e}. Raw: {response.content[:300]}")

        return {
            "intent": "unsupported",
            "sheet_key": "",
            "target_columns": [],
            "filters": [],
            "group_by": [],
            "sort_by": {},
            "limit": 10,
            "aggregation": "none",
            "explanation_mode": "normal",
        }

    # =========================
    # Execution
    # =========================

    def _select_df_for_plan(self, plan: dict) -> Optional[pd.DataFrame]:
        """
        Pick the right DataFrame based on the LLM-selected sheet_key in the plan.
        Falls back to the largest sheet only if no usable sheet_key is found.
        """
        sheet_key = plan.get("sheet_key", "").strip()

        # Exact match
        if sheet_key and sheet_key in self._cache:
            logger.info(f"Excel: using exact sheet '{sheet_key}'")
            return self._cache[sheet_key]

        # Partial match — sheet name portion after "::"
        if sheet_key:
            sheet_name_hint = sheet_key.split("::", 1)[-1].lower()
            for key in self._cache:
                if sheet_name_hint in key.lower():
                    logger.info(f"Excel: partial-matched sheet '{key}' from hint '{sheet_key}'")
                    return self._cache[key]
            logger.warning(
                f"Excel: sheet_key '{sheet_key}' not found. Available: {list(self._cache.keys())}. Falling back."
            )

        return self._get_best_df()

    def _apply_filters(self, df: pd.DataFrame, filters: List[dict]) -> pd.DataFrame:
        result = df.copy()

        for f in filters:
            col = f.get("column")
            op = f.get("operator")
            val = f.get("value")

            if col not in result.columns:
                logger.warning(f"Filter column '{col}' not found. Available: {list(result.columns)}")
                continue

            series = result[col]

            # --- Numeric operators ---
            if op in {"gt", "gte", "lt", "lte"}:
                numeric_series = pd.to_numeric(series, errors="coerce")
                try:
                    numeric_val = float(val)
                except Exception:
                    continue
                if op == "gt":
                    result = result[numeric_series > numeric_val]
                elif op == "gte":
                    result = result[numeric_series >= numeric_val]
                elif op == "lt":
                    result = result[numeric_series < numeric_val]
                elif op == "lte":
                    result = result[numeric_series <= numeric_val]

            # --- Equality ---
            elif op == "equals":
                result = result[series.astype(str).str.strip().str.lower() == str(val).strip().lower()]

            elif op == "not_equals":
                result = result[series.astype(str).str.strip().str.lower() != str(val).strip().lower()]

            # --- Text search ---
            elif op == "contains":
                result = result[series.astype(str).str.lower().str.contains(str(val).lower(), na=False)]

            # --- Date operators ---
            elif op == "date_month":
                # val format: "YYYY-MM" e.g. "2024-01"
                try:
                    dt_series = pd.to_datetime(series, errors="coerce")
                    period = pd.Period(str(val), freq="M")
                    result = result[dt_series.dt.to_period("M") == period]
                except Exception as e:
                    logger.warning(f"date_month filter failed: {e}")

            elif op == "date_year":
                # val format: "YYYY" e.g. "2024"
                try:
                    dt_series = pd.to_datetime(series, errors="coerce")
                    result = result[dt_series.dt.year == int(val)]
                except Exception as e:
                    logger.warning(f"date_year filter failed: {e}")

            elif op == "date_range":
                # val format: "YYYY-MM-DD,YYYY-MM-DD"
                try:
                    parts = str(val).split(",", 1)
                    start = pd.to_datetime(parts[0].strip())
                    end = pd.to_datetime(parts[1].strip())
                    dt_series = pd.to_datetime(series, errors="coerce")
                    result = result[(dt_series >= start) & (dt_series <= end)]
                except Exception as e:
                    logger.warning(f"date_range filter failed: {e}")

        return result

    def _execute_plan(self, query: str, plan: dict) -> dict:
        intent = plan.get("intent", "unsupported")

        # Ratio intent needs special handling (two separate filter counts)
        if intent == "ratio":
            return self._execute_ratio(plan)

        df = self._select_df_for_plan(plan)
        if df is None or df.empty:
            return {"status": "error", "message": "No Excel data available."}
        logger.info(
            f"Excel execute: sheet_key='{plan.get('sheet_key')}' df.shape={df.shape} intent={intent}"
        )

        if intent == "followup_last_results":
            return {
                "status": "error",
                "message": "Follow-up results should be resolved from session memory before execution."
            }

        target_columns = plan.get("target_columns", [])
        filters = plan.get("filters", [])
        group_by = plan.get("group_by", [])
        sort_by = plan.get("sort_by", {})
        limit = int(plan.get("limit", 10) or 10)
        aggregation = plan.get("aggregation", "none")

        result_df = self._apply_filters(df, filters)
        logger.info(f"After filters: {len(result_df)} rows (was {len(df)})")

        sort_col = sort_by.get("column") if isinstance(sort_by, dict) else None
        sort_order = sort_by.get("order", "asc") if isinstance(sort_by, dict) else "asc"
        if sort_col and sort_col in result_df.columns:
            temp = result_df.copy()
            temp[sort_col] = pd.to_numeric(temp[sort_col], errors="ignore")
            result_df = temp.sort_values(by=sort_col, ascending=(sort_order != "desc"))

        # --- group_count: "most common X", "which X has most" ---
        if intent == "group_count":
            if not group_by:
                return {"status": "error", "message": "No group_by column specified for group_count."}
            group_col = group_by[0]
            if group_col not in result_df.columns:
                return {"status": "error", "message": f"Column '{group_col}' not found."}

            counts = (
                result_df.groupby(group_col, dropna=True)
                .size()
                .sort_values(ascending=False)
                .reset_index(name="count")
            )
            top_value = str(counts.iloc[0][group_col]) if not counts.empty else None
            top_count = int(counts.iloc[0]["count"]) if not counts.empty else 0

            return {
                "status": "ok",
                "intent": "group_count",
                "group_column": group_col,
                "top_value": top_value,
                "top_count": top_count,
                "rows": counts.head(limit).to_dict(orient="records"),
                "row_count": len(counts),
                "columns": [group_col, "count"],
            }

        # --- lookup / filter / rank ---
        if intent in {"lookup", "filter", "rank"}:
            if result_df.empty:
                return {
                    "status": "ok",
                    "intent": intent,
                    "rows": [],
                    "row_count": 0,
                    "columns": list(result_df.columns),
                }

            if target_columns:
                keep_cols = [c for c in target_columns if c in result_df.columns]
                if keep_cols:
                    result_df = result_df[keep_cols]

            result_df = result_df.head(limit)
            return {
                "status": "ok",
                "intent": intent,
                "rows": result_df.fillna("").to_dict(orient="records"),
                "row_count": len(result_df),
                "columns": list(result_df.columns),
            }

        # --- count ---
        if intent == "count" or aggregation == "count":
            return {
                "status": "ok",
                "intent": "count",
                "value": int(len(result_df)),
            }

        # --- aggregate (sum / average / min / max) ---
        if intent == "aggregate":
            if not target_columns:
                return {"status": "error", "message": "No target column for aggregation."}

            col = target_columns[0]
            if col not in result_df.columns:
                return {"status": "error", "message": f"Column '{col}' not found."}

            numeric_col = pd.to_numeric(result_df[col], errors="coerce").dropna()
            if numeric_col.empty:
                return {"status": "error", "message": f"Column '{col}' has no numeric values."}

            if aggregation == "sum":
                value = float(numeric_col.sum())
            elif aggregation == "average":
                value = float(numeric_col.mean())
            elif aggregation == "min":
                value = float(numeric_col.min())
            elif aggregation == "max":
                value = float(numeric_col.max())
            else:
                return {"status": "error", "message": f"Unsupported aggregation: {aggregation}"}

            return {
                "status": "ok",
                "intent": "aggregate",
                "aggregation": aggregation,
                "column": col,
                "value": value,
                "row_count": len(result_df),
            }

        # --- compare: group_by + numeric aggregation ---
        if intent == "compare":
            if not group_by:
                return {"status": "error", "message": "No group_by column for compare."}

            group_col = group_by[0]
            if group_col not in result_df.columns:
                return {"status": "error", "message": f"Group column '{group_col}' not found."}

            # If no target column → fall back to count by group (same as group_count)
            if not target_columns:
                counts = (
                    result_df.groupby(group_col, dropna=True)
                    .size()
                    .sort_values(ascending=False)
                    .reset_index(name="count")
                )
                return {
                    "status": "ok",
                    "intent": "group_count",
                    "group_column": group_col,
                    "top_value": str(counts.iloc[0][group_col]) if not counts.empty else None,
                    "top_count": int(counts.iloc[0]["count"]) if not counts.empty else 0,
                    "rows": counts.head(limit).to_dict(orient="records"),
                    "row_count": len(counts),
                    "columns": [group_col, "count"],
                }

            target_col = target_columns[0]
            if target_col not in result_df.columns:
                return {"status": "error", "message": f"Target column '{target_col}' not found."}

            temp = result_df.copy()
            temp[target_col] = pd.to_numeric(temp[target_col], errors="coerce")
            temp = temp.dropna(subset=[target_col])

            grouped = (
                temp.groupby(group_col)[target_col]
                .mean()
                .sort_values(ascending=False)
                .reset_index()
            )
            grouped = grouped.head(limit)

            return {
                "status": "ok",
                "intent": "compare",
                "rows": grouped.fillna("").to_dict(orient="records"),
                "row_count": len(grouped),
                "columns": list(grouped.columns),
            }

        return {
            "status": "error",
            "message": f"Unsupported or unresolved intent: {intent}",
        }

    def _execute_ratio(self, plan: dict) -> dict:
        """
        Computes numerator_count / denominator_count as a percentage.
        Both counts come from the same sheet.
        """
        df = self._select_df_for_plan(plan)
        if df is None or df.empty:
            return {"status": "error", "message": "No Excel data available."}

        numerator_filters = plan.get("numerator_filters", plan.get("filters", []))
        denominator_filters = plan.get("denominator_filters", [])

        numerator_df = self._apply_filters(df, numerator_filters)
        denominator_df = self._apply_filters(df, denominator_filters) if denominator_filters else df

        numerator = len(numerator_df)
        denominator = len(denominator_df)
        percentage = round((numerator / denominator * 100), 2) if denominator > 0 else 0.0

        logger.info(
            f"Excel ratio: numerator={numerator} denominator={denominator} pct={percentage}%"
        )

        return {
            "status": "ok",
            "intent": "ratio",
            "numerator": numerator,
            "denominator": denominator,
            "percentage": percentage,
        }

    # =========================
    # Answer Composition
    # =========================

    def _compose_answer(self, query: str, plan: dict, execution_result: dict) -> str:
        prompt = (
            EXCEL_ANSWER_PROMPT
            + "\n\n"
            + f"User question: {query}\n"
            + f"Query plan: {json.dumps(plan, ensure_ascii=False)}\n"
            + f"Execution result: {json.dumps(execution_result, ensure_ascii=False)}\n"
            + f"Schema hints: {json.dumps(self._get_schema_summary(), ensure_ascii=False)}"
        )

        response = self._llm.invoke(prompt)
        return response.content.strip()

    # =========================
    # Public API
    # =========================

    def answer_query(self, query: str, session_id: str = "default", memory_service=None) -> str:
        if not self._cache:
            self.refresh()

        if not self._cache:
            return "I couldn't find any uploaded Excel data to answer that question."

        try:
            followup = self._resolve_followup(query, session_id=session_id, memory_service=memory_service)

            if followup.get("mode") == "reuse_last_result" and memory_service is not None:
                last_result = memory_service.get_structured_state(session_id, "last_excel_result", None)
                if last_result:
                    return self._compose_answer(query, {"intent": "followup_last_results"}, last_result)
                return "I couldn't find any previous matched customer list in this session."

            resolved_query = followup.get("resolved_query", query)
            plan = self._plan_query(resolved_query)

            if plan.get("intent") == "unsupported":
                return "This looks like an Excel-related question, but I could not map it reliably to the uploaded spreadsheet structure."

            execution_result = self._execute_plan(resolved_query, plan)

            if execution_result.get("status") == "error":
                return execution_result.get("message", "I encountered an error while analyzing the uploaded Excel data.")

            if memory_service is not None:
                memory_service.set_structured_state(session_id, "last_excel_result", execution_result)
                memory_service.set_structured_state(session_id, "last_excel_query", query)
                memory_service.set_structured_state(session_id, "last_excel_plan", plan)

            return self._compose_answer(query, plan, execution_result)

        except Exception as e:
            logger.error(f"Excel intelligent query failed: {e}", exc_info=True)
            return "I encountered an error while analyzing the uploaded Excel data."


excel_query_service = ExcelQueryService()

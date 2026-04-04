import json
import logging
from typing import Literal, List, Tuple

from langchain_openai import ChatOpenAI

from app.config import settings
from app.prompts.excel_prompts import DYNAMIC_ROUTER_PROMPT

logger = logging.getLogger(__name__)

RouteType = Literal["EXCEL_QUERY", "RAG_QUERY", "MIXED_QUERY", "RULE_QUERY"]


class RouterService:
    """
    Dynamic router:
    - uses LLM routing first
    - keeps a small safe fallback if LLM fails
    """

    def __init__(self):
        self._llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.0,
            max_tokens=300,
            openai_api_key=settings.OPENAI_API_KEY,
        )

    def _format_history(self, chat_history: List[Tuple[str, str]]) -> str:
        if not chat_history:
            return "No prior chat history."
        parts = []
        for human, ai in chat_history[-3:]:
            parts.append(f"User: {human}\nAssistant: {ai[:200]}")
        return "\n\n".join(parts)

    def _fallback_route(self, query: str) -> RouteType:
        q = query.lower().strip()

        if any(x in q for x in [
            "based on brd",
            "based on the brd",
            "based on process",
            "based on rules",
            "according to the rules",
            "which customers need review",
            "who should be prioritized",
            "which cases need escalation",
            "which customers need monitoring",
            "apply the rule",
        ]):
            return "RULE_QUERY"

        if any(x in q for x in [
            "how many customers", "count of customers", "how many records",
            "highest risk customer", "lowest risk", "average onboarding",
            "average duration", "maximum duration", "minimum duration",
            "which customers have", "which members have",
            "customers with risk", "onboarding time", "onboarding duration",
            "tat", "cust-",
        ]):
            return "EXCEL_QUERY"

        return "RAG_QUERY"

    def route_query(
        self,
        query: str,
        chat_history: List[Tuple[str, str]] = None,
        source_summary: str = ""
    ) -> RouteType:
        chat_history = chat_history or []

        prompt = (
            DYNAMIC_ROUTER_PROMPT
            + "\n\n"
            + f"User query: {query}\n"
            + f"Chat history: {self._format_history(chat_history)}\n"
            + f"Available source capabilities: {source_summary or 'RAG documents, Excel structured data, BRD/rule execution'}"
        )

        try:
            response = self._llm.invoke(prompt)
            parsed = json.loads(response.content.strip())
            route = parsed.get("route", "").strip()

            if route in {"RAG_QUERY", "EXCEL_QUERY", "RULE_QUERY", "MIXED_QUERY"}:
                logger.info(f"Dynamic router selected {route} | reason={parsed.get('reason')} | confidence={parsed.get('confidence')}")
                return route  # type: ignore

        except Exception as e:
            logger.warning(f"Dynamic router failed, using fallback: {e}")

        fallback = self._fallback_route(query)
        logger.info(f"Fallback router selected {fallback}")
        return fallback


router_service = RouterService()
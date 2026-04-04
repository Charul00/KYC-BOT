import logging
from typing import List, Tuple, Dict, Any

from app.services.excel_service import excel_query_service
from app.services.rule_service import rule_execution_service
from app.services.rag_service import rag_service
from app.services.router_service import router_service
from app.services.file_registry_service import file_registry_service

logger = logging.getLogger(__name__)


class OrchestratorService:
    """
    Central source-aware orchestrator.

    It decides how to handle a query using:
    - router
    - file registry summary
    - excel service
    - rule service
    - rag service
    """

    async def answer_query(
        self,
        query: str,
        session_id: str,
        chat_history: List[Tuple[str, str]],
        memory_service,
    ) -> Dict[str, Any]:
        source_summary = file_registry_service.get_source_summary()

        route_type = router_service.route_query(
            query,
            chat_history=chat_history,
            source_summary=source_summary,
        )

        logger.info(f"Orchestrator route={route_type} | source_summary={source_summary}")

        if route_type == "RULE_QUERY":
            answer = rule_execution_service.answer_query(query)
            return {
                "route_type": route_type,
                "answer": answer,
                "source_documents": [],
                "query_type": "RULE_QUERY",
            }

        if route_type == "EXCEL_QUERY":
            answer = excel_query_service.answer_query(
                query,
                session_id=session_id,
                memory_service=memory_service,
            )
            return {
                "route_type": route_type,
                "answer": answer,
                "source_documents": [],
                "query_type": "EXCEL_QUERY",
            }

        if route_type == "MIXED_QUERY":
            excel_answer = excel_query_service.answer_query(
                query,
                session_id=session_id,
                memory_service=memory_service,
            )

            rag_result = await rag_service.get_answer(
                query=query,
                chat_history=chat_history,
            )

            rag_answer = rag_result["answer"]
            source_docs = rag_result.get("source_documents", [])

            # Detect whether Excel actually returned useful data.
            # Common "no data" phrases returned by excel_query_service:
            _excel_no_data_signals = [
                "couldn't find any uploaded excel",
                "no excel",
                "no spreadsheet",
                "no structured data",
                "no data found",
                "not found in the spreadsheet",
                "no uploaded excel",
            ]
            excel_has_data = not any(
                sig in excel_answer.lower() for sig in _excel_no_data_signals
            )

            if excel_has_data:
                # Both sources have useful content — show both clearly
                final_answer = (
                    "From the uploaded structured data:\n"
                    f"{excel_answer}\n\n"
                    "From the uploaded document context:\n"
                    f"{rag_answer}"
                )
            else:
                # Excel had nothing useful — just return the RAG answer cleanly
                final_answer = rag_answer

            return {
                "route_type": route_type,
                "answer": final_answer,
                "source_documents": source_docs,
                "query_type": "MIXED_QUERY",
            }

        rag_result = await rag_service.get_answer(
            query=query,
            chat_history=chat_history,
        )

        return {
            "route_type": route_type,
            "answer": rag_result["answer"],
            "source_documents": rag_result.get("source_documents", []),
            "query_type": rag_result.get("query_type", "SIMPLE"),
        }


orchestrator_service = OrchestratorService()
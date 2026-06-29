"""
Autopilot Agent Tool: Audit Record Writer

Persists the final state of an autopilot workflow run to the database,
creating an immutable audit trail with timestamps for each step.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def tool_write_audit_record(
    invoice_id: str,
    workflow_id: str,
    final_status: str,
    summary_json: str,
) -> str:
    """
    Write the final audit record to the database for compliance and traceability.

    Args:
        invoice_id: Integer invoice ID.
        workflow_id: UUID string of the Celery workflow run.
        final_status: One of "approved" | "disputed" | "escalated" | "pending_hitl".
        summary_json: JSON string with workflow summary data (anomalies, dispute_letter_id, etc.).

    Returns:
        JSON string: {"audit_record_id": int, "status": "written"}
        or {"error": "..."} on failure.
    """
    from app.database import async_session_factory
    from app.models import AuditRecord

    logger.info(
        f"[TOOL:db_writer] Writing audit record for "
        f"invoice_id={invoice_id}, workflow_id={workflow_id}, status={final_status}"
    )

    valid_statuses = {"approved", "disputed", "escalated", "pending_hitl"}
    if final_status.lower() not in valid_statuses:
        return json.dumps({
            "error": f"Invalid final_status '{final_status}'. "
                     f"Must be one of {valid_statuses}"
        })

    try:
        summary_data = json.loads(summary_json)
    except json.JSONDecodeError as exc:
        summary_data = {"raw": summary_json, "parse_error": str(exc)}

    async with async_session_factory() as db:
        record = AuditRecord(
            invoice_id=int(invoice_id),
            workflow_id=workflow_id,
            final_status=final_status.lower(),
            summary=summary_data,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        record_id = record.id

    logger.info(
        f"[TOOL:db_writer] Audit record written: id={record_id}, "
        f"status={final_status}"
    )
    return json.dumps({"audit_record_id": record_id, "status": "written"})

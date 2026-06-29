"""
Autopilot Agent Tool: HITL Checkpoint

Creates, checks, and manages Human-in-the-Loop checkpoint records.
Three gate types are supported:
  HITL-1: UNMAPPED_CHARGE  — unmapped invoice charge needs manual mapping
  HITL-2: HIGH_VALUE_ANOMALY — high-severity anomaly needs client approval
  HITL-3: DISPUTE_APPROVAL — dispute letter ready for final review before dispatch
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

GATE_ESCALATION_HOURS = {
    "UNMAPPED_CHARGE": 24,
    "HIGH_VALUE_ANOMALY": 48,
    "DISPUTE_APPROVAL": 72,
}


@tool
async def tool_check_hitl_required(
    workflow_id: str,
    invoice_id: str,
    tenant_id: str,
    gate_type: str,
    context_json: str,
) -> str:
    """
    Create a HITL checkpoint in the database, notify the reviewer, and
    return a status string so the orchestrator can decide whether to pause.

    gate_type must be one of:
      UNMAPPED_CHARGE    — HITL-1: charge mapping review
      HIGH_VALUE_ANOMALY — HITL-2: anomaly approval
      DISPUTE_APPROVAL   — HITL-3: dispute letter sign-off

    Args:
        workflow_id: Unique identifier for this workflow run (UUID string).
        invoice_id: Integer invoice ID being processed.
        tenant_id: Integer company ID of the client tenant.
        gate_type: One of the gate types above.
        context_json: JSON string with gate-specific payload for the reviewer.

    Returns:
        One of:
        "PAUSED:<checkpoint_id>"   — checkpoint created, workflow must pause
        "APPROVED:<checkpoint_id>" — checkpoint already approved, workflow proceeds
        "AUTO_PROCEED"             — no checkpoint needed (conditions not met)
        "ERROR:<message>"          — something went wrong
    """
    from app.database import async_session_factory
    from app.models import HitlCheckpoint, HitlGateType, HitlStatus
    from sqlalchemy import select

    valid_gates = {"UNMAPPED_CHARGE", "HIGH_VALUE_ANOMALY", "DISPUTE_APPROVAL"}
    if gate_type not in valid_gates:
        return f"ERROR:Invalid gate_type '{gate_type}'. Must be one of {valid_gates}"

    try:
        context_data = json.loads(context_json)
    except json.JSONDecodeError as exc:
        return f"ERROR:Invalid context_json — {exc}"

    escalate_hours = GATE_ESCALATION_HOURS.get(gate_type, 24)
    now = datetime.now(timezone.utc)

    async with async_session_factory() as db:
        # Check if this workflow+gate already has an APPROVED checkpoint
        existing_result = await db.execute(
            select(HitlCheckpoint).where(
                HitlCheckpoint.workflow_id == workflow_id,
                HitlCheckpoint.gate_type == HitlGateType(gate_type),
                HitlCheckpoint.status == HitlStatus.APPROVED,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            logger.info(
                f"[TOOL:hitl] Gate {gate_type} already APPROVED "
                f"(checkpoint_id={existing.id})"
            )
            return f"APPROVED:{existing.id}"

        # Create new PENDING checkpoint
        checkpoint = HitlCheckpoint(
            workflow_id=workflow_id,
            invoice_id=int(invoice_id),
            tenant_id=int(tenant_id),
            gate_type=HitlGateType(gate_type),
            status=HitlStatus.PENDING,
            context_data=context_data,
            created_at=now,
            escalate_after=now + timedelta(hours=escalate_hours),
        )
        db.add(checkpoint)
        await db.commit()
        await db.refresh(checkpoint)
        checkpoint_id = checkpoint.id

    # Fire notification (non-blocking — best-effort)
    try:
        from app.tasks.escalation import send_hitl_notification_task
        send_hitl_notification_task.delay(str(checkpoint_id), gate_type, context_json)
    except Exception as notify_exc:
        logger.warning(f"[TOOL:hitl] Notification task failed: {notify_exc}")

    logger.info(
        f"[TOOL:hitl] PAUSED: Created {gate_type} checkpoint "
        f"id={checkpoint_id} for workflow={workflow_id}"
    )
    return f"PAUSED:{checkpoint_id}"

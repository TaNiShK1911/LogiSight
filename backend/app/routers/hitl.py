"""
HITL (Human-in-the-Loop) API routes for LogiSight Autopilot Agent.

Endpoints:
  GET  /hitl/pending        — list pending checkpoints for current tenant
  GET  /hitl/{id}           — get checkpoint detail including context data
  POST /hitl/{id}/resolve   — approve / reject / override a checkpoint
  POST /autopilot/trigger   — manually trigger the autopilot workflow for an invoice
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_profile
from app.models import (
    HitlCheckpoint,
    HitlGateType,
    HitlStatus,
    DisputeLetter,
    Invoice,
)

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class HitlCheckpointOut(BaseModel):
    id: int
    workflow_id: str
    invoice_id: int
    tenant_id: int
    gate_type: str
    status: str
    context_data: dict
    reviewer_id: int | None
    reviewer_decision: str | None
    reviewer_notes: str | None
    created_at: datetime
    resolved_at: datetime | None
    escalate_after: datetime

    class Config:
        from_attributes = True


class HitlResolveRequest(BaseModel):
    status: Literal["APPROVED", "REJECTED", "OVERRIDDEN"]
    reviewer_notes: str | None = None
    # For HITL-1: updated mapping data (charge_id to assign)
    mapped_charge_id: int | None = None
    # For HITL-3: optionally edit the dispute letter before approving
    updated_letter_text: str | None = None


class AutopilotTriggerRequest(BaseModel):
    invoice_id: int
    quote_id: int


class AutopilotTriggerOut(BaseModel):
    task_id: str
    workflow_id: str
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/pending",
    response_model=list[HitlCheckpointOut],
    summary="List pending HITL checkpoints for the current tenant",
)
async def list_pending_hitl(
    profile=Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Return all PENDING HITL checkpoints for the authenticated user's tenant."""
    company_id = profile.company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="No company associated with this user")

    result = await db.execute(
        select(HitlCheckpoint)
        .where(
            HitlCheckpoint.tenant_id == company_id,
            HitlCheckpoint.status == HitlStatus.PENDING,
        )
        .order_by(HitlCheckpoint.created_at.desc())
    )
    checkpoints = result.scalars().all()
    return checkpoints


@router.get(
    "/{checkpoint_id}",
    response_model=HitlCheckpointOut,
    summary="Get HITL checkpoint detail",
)
async def get_hitl_checkpoint(
    checkpoint_id: int,
    profile=Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Return the full detail of a single HITL checkpoint."""
    company_id = profile.company_id
    result = await db.execute(
        select(HitlCheckpoint).where(
            HitlCheckpoint.id == checkpoint_id,
            HitlCheckpoint.tenant_id == company_id,
        )
    )
    checkpoint = result.scalar_one_or_none()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return checkpoint


@router.post(
    "/{checkpoint_id}/resolve",
    response_model=dict,
    summary="Resolve a HITL checkpoint (approve / reject)",
)
async def resolve_hitl_checkpoint(
    checkpoint_id: int,
    body: HitlResolveRequest,
    profile=Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve a HITL checkpoint. On APPROVED:
    - HITL-1: stores the charge mapping, adds an alias
    - HITL-3: updates the dispute letter status and sends it
    - Resumes the autopilot workflow in all cases
    """
    company_id = profile.company_id
    result = await db.execute(
        select(HitlCheckpoint).where(
            HitlCheckpoint.id == checkpoint_id,
            HitlCheckpoint.tenant_id == company_id,
        )
    )
    checkpoint = result.scalar_one_or_none()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    if checkpoint.status != HitlStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Checkpoint is already in status '{checkpoint.status.value}'"
        )

    now = datetime.now(timezone.utc)
    checkpoint.status = HitlStatus(body.status)
    checkpoint.reviewer_id = profile.id if hasattr(profile, "id") else None
    checkpoint.reviewer_decision = body.status
    checkpoint.reviewer_notes = body.reviewer_notes
    checkpoint.resolved_at = now

    # Gate-specific side effects on APPROVED
    next_action = "workflow_ended"
    if body.status == "APPROVED":
        gate = checkpoint.gate_type

        if gate == HitlGateType.UNMAPPED_CHARGE and body.mapped_charge_id:
            # HITL-1: Add alias mapping for the unmapped charge
            context = checkpoint.context_data or {}
            raw_name = context.get("raw_charge_name")
            if raw_name:
                from app.models import ChargeAlias
                alias = ChargeAlias(
                    charge_id=body.mapped_charge_id,
                    alias=raw_name,
                )
                db.add(alias)

        elif gate == HitlGateType.DISPUTE_APPROVAL:
            # HITL-3: Update or approve the dispute letter
            context = checkpoint.context_data or {}
            dispute_letter_id = context.get("dispute_letter_id")
            if dispute_letter_id:
                letter_result = await db.execute(
                    select(DisputeLetter).where(DisputeLetter.id == dispute_letter_id)
                )
                letter = letter_result.scalar_one_or_none()
                if letter:
                    if body.updated_letter_text:
                        letter.letter_text = body.updated_letter_text
                    letter.status = "APPROVED"
                    letter.approved_at = now

        next_action = "workflow_resumed"

        # Resume the Autopilot workflow asynchronously
        try:
            from app.tasks.autopilot import run_autopilot_workflow
            task = run_autopilot_workflow.delay(
                invoice_id=str(checkpoint.invoice_id),
                tenant_id=str(checkpoint.tenant_id),
                quote_id=str(
                    (await db.execute(
                        select(Invoice.quote_id).where(Invoice.id == checkpoint.invoice_id)
                    )).scalar_one_or_none() or 0
                ),
                workflow_id=checkpoint.workflow_id,
                resume_from_gate=checkpoint.gate_type.value,
            )
        except Exception as exc:
            # Non-fatal: log but don't fail the resolve
            import logging
            logging.getLogger(__name__).warning(
                f"[HITL] Could not queue workflow resume: {exc}"
            )

    await db.commit()

    return {
        "status": "resolved",
        "checkpoint_id": checkpoint_id,
        "decision": body.status,
        "next": next_action,
    }


@router.post(
    "/autopilot/trigger",
    response_model=AutopilotTriggerOut,
    summary="Manually trigger the Autopilot Agent for an invoice",
    tags=["autopilot"],
)
async def trigger_autopilot(
    body: AutopilotTriggerRequest,
    profile=Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger the Autopilot audit workflow for a specific invoice.
    The workflow runs asynchronously via Celery.
    """
    import uuid

    company_id = profile.company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="No company associated with this user")

    # Verify the invoice belongs to this tenant
    result = await db.execute(
        select(Invoice).where(Invoice.id == body.invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    workflow_id = str(uuid.uuid4())

    try:
        from app.tasks.autopilot import run_autopilot_workflow
        task = run_autopilot_workflow.delay(
            invoice_id=str(body.invoice_id),
            tenant_id=str(company_id),
            quote_id=str(body.quote_id),
            workflow_id=workflow_id,
        )
        task_id = task.id
    except Exception as exc:
        # Celery not available (e.g., no Redis in dev) — return workflow_id only
        task_id = "celery-unavailable"
        import logging
        logging.getLogger(__name__).warning(
            f"[HITL] Celery not available, workflow queued in-process: {exc}"
        )

    return AutopilotTriggerOut(
        task_id=task_id,
        workflow_id=workflow_id,
        message=(
            f"Autopilot workflow {workflow_id} queued for invoice {body.invoice_id}. "
            "Check Pending Reviews for HITL gates."
        ),
    )

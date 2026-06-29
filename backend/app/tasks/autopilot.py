"""
Main Autopilot Workflow — Celery Task.

Orchestrates the full freight audit pipeline using the Qwen-Max tool-calling agent.
Supports both fresh runs and resume-from-gate for HITL workflow resumption.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.celery_app import app

logger = logging.getLogger(__name__)


@app.task(
    name="tasks.run_autopilot_workflow",
    queue="autopilot",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def run_autopilot_workflow(
    self,
    invoice_id: str,
    tenant_id: str,
    quote_id: str,
    workflow_id: str | None = None,
    resume_from_gate: str | None = None,
) -> dict:
    """
    Main Autopilot Agent task.

    Args:
        invoice_id: Integer invoice ID to process.
        tenant_id: Integer tenant/company ID (client).
        quote_id: Integer quote ID to compare against.
        workflow_id: Unique workflow run ID (auto-generated if None).
        resume_from_gate: Gate type to resume from after HITL approval
                          (UNMAPPED_CHARGE | HIGH_VALUE_ANOMALY | DISPUTE_APPROVAL).

    Returns:
        Dict with "status" and "output" keys.
    """
    if not workflow_id:
        workflow_id = str(uuid.uuid4())

    logger.info(
        f"[AUTOPILOT] Starting workflow_id={workflow_id} | "
        f"invoice_id={invoice_id} | tenant_id={tenant_id} | "
        f"quote_id={quote_id} | resume_from_gate={resume_from_gate}"
    )

    resume_note = (
        f" Resuming after HITL gate '{resume_from_gate}' was approved."
        if resume_from_gate
        else ""
    )

    try:
        from app.agent.orchestrator import create_autopilot_agent

        executor = create_autopilot_agent()

        result = executor.invoke({
            "input": (
                f"Process invoice_id={invoice_id} for tenant_id={tenant_id}. "
                f"Compare against quote_id={quote_id}. "
                f"Use workflow_id={workflow_id} for all HITL checkpoint calls.{resume_note} "
                f"Follow the full audit workflow as defined in your instructions."
            )
        })

        output = result.get("output", "")
        logger.info(f"[AUTOPILOT] Workflow {workflow_id} completed: {output[:200]}")

        status = "paused" if "WORKFLOW_PAUSED" in output else "completed"
        return {"status": status, "workflow_id": workflow_id, "output": output}

    except Exception as exc:
        logger.exception(f"[AUTOPILOT] Workflow {workflow_id} failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(f"[AUTOPILOT] Max retries exceeded for workflow {workflow_id}")
            return {
                "status": "failed",
                "workflow_id": workflow_id,
                "error": str(exc),
            }

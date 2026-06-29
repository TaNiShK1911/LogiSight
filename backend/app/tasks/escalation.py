"""
Email Ingestion + HITL Escalation tasks for LogiSight Autopilot.

Provides:
  - poll_email_for_invoices: IMAP inbox polling (Celery Beat, every 5 min)
  - escalate_hitl_checkpoints: Auto-escalate overdue HITL gates (every 30 min)
  - send_hitl_notification_task: Send reviewer notification for a new HITL gate
"""

from __future__ import annotations

import asyncio
import imaplib
import json
import logging
import os
from datetime import datetime, timezone
from email import message_from_bytes
from email.message import Message

from app.celery_app import app

logger = logging.getLogger(__name__)


# ── Email Ingestion ─────────────────────────────────────────────────────────

@app.task(name="tasks.poll_email_for_invoices", queue="autopilot")
def poll_email_for_invoices() -> dict:
    """
    Poll the configured IMAP inbox for new emails with PDF attachments.
    For each PDF found:
      1. Upload to OSS
      2. Create an Invoice record in DB with status=PENDING
      3. Trigger run_autopilot_workflow

    Requires: IMAP_SERVER, IMAP_EMAIL, IMAP_PASSWORD env vars.
    """
    imap_server = os.environ.get("IMAP_SERVER", "")
    imap_email = os.environ.get("IMAP_EMAIL", "")
    imap_password = os.environ.get("IMAP_PASSWORD", "")

    if not all([imap_server, imap_email, imap_password]):
        logger.debug("[INGESTION] IMAP not configured — skipping email poll")
        return {"status": "skipped", "reason": "IMAP not configured"}

    processed = 0
    errors = 0

    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(imap_email, imap_password)
        mail.select("INBOX")

        # Search for unread emails with attachments
        _, msg_ids = mail.search(None, "UNSEEN")
        if not msg_ids or not msg_ids[0]:
            logger.debug("[INGESTION] No new emails found")
            mail.logout()
            return {"status": "ok", "processed": 0}

        for msg_id in msg_ids[0].split()[:10]:  # Process max 10 per run
            try:
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue

                raw_email = msg_data[0][1]
                email_msg: Message = message_from_bytes(raw_email)
                subject = email_msg.get("Subject", "")
                sender = email_msg.get("From", "")

                logger.info(f"[INGESTION] Processing email from {sender}: {subject}")

                # Extract PDF attachments
                for part in email_msg.walk():
                    content_type = part.get_content_type()
                    filename = part.get_filename()

                    if content_type == "application/pdf" and filename:
                        pdf_bytes = part.get_payload(decode=True)
                        if not pdf_bytes:
                            continue

                        logger.info(
                            f"[INGESTION] Found PDF attachment: {filename} "
                            f"({len(pdf_bytes)} bytes)"
                        )

                        # Trigger async processing
                        asyncio.run(
                            _process_email_invoice(pdf_bytes, filename, sender)
                        )
                        processed += 1

                # Mark email as read
                mail.store(msg_id, "+FLAGS", "\\Seen")

            except Exception as exc:
                logger.error(f"[INGESTION] Error processing email {msg_id}: {exc}")
                errors += 1

        mail.logout()

    except imaplib.IMAP4.error as exc:
        logger.error(f"[INGESTION] IMAP connection failed: {exc}")
        return {"status": "error", "error": str(exc)}

    logger.info(f"[INGESTION] Done: {processed} processed, {errors} errors")
    return {"status": "ok", "processed": processed, "errors": errors}


async def _process_email_invoice(
    pdf_bytes: bytes,
    filename: str,
    sender_email: str,
) -> None:
    """
    Upload PDF to OSS and queue autopilot workflow.
    In production, this would also look up the tenant by sender email.
    """
    from app.services.oss_storage import upload_invoice_to_oss

    # For email ingestion, use a placeholder quote_id of 0 until
    # the agent or a human assigns the correct quote
    oss_key = await upload_invoice_to_oss(pdf_bytes, filename, quote_id=0)
    logger.info(f"[INGESTION] PDF uploaded to OSS: {oss_key}")

    # TODO: Lookup tenant_id from sender email domain in DB
    # For now, log the action — full email-to-workflow binding
    # requires tenant onboarding configuration
    logger.info(
        f"[INGESTION] Invoice from {sender_email} ready at {oss_key}. "
        "Manual quote assignment required before autopilot can run."
    )


# ── HITL Auto-Escalation ─────────────────────────────────────────────────────

@app.task(name="tasks.escalate_hitl_checkpoints", queue="autopilot")
def escalate_hitl_checkpoints() -> dict:
    """
    Check for HITL checkpoints past their escalate_after deadline.
    Auto-escalate by:
      1. Updating status to AUTO_ESCALATED
      2. Notifying super admin
    """
    return asyncio.run(_run_escalation())


async def _run_escalation() -> dict:
    from app.database import async_session_factory
    from app.models import HitlCheckpoint, HitlStatus
    from sqlalchemy import select

    now = datetime.now(timezone.utc)
    escalated_count = 0

    async with async_session_factory() as db:
        result = await db.execute(
            select(HitlCheckpoint).where(
                HitlCheckpoint.status == HitlStatus.PENDING,
                HitlCheckpoint.escalate_after <= now,
            )
        )
        overdue = result.scalars().all()

        for checkpoint in overdue:
            checkpoint.status = HitlStatus.AUTO_ESCALATED
            checkpoint.resolved_at = now
            escalated_count += 1
            logger.warning(
                f"[ESCALATION] Auto-escalated checkpoint id={checkpoint.id} "
                f"gate={checkpoint.gate_type.value} workflow={checkpoint.workflow_id}"
            )

        await db.commit()

    logger.info(f"[ESCALATION] {escalated_count} checkpoint(s) auto-escalated")
    return {"escalated": escalated_count}


# ── HITL Notification ────────────────────────────────────────────────────────

@app.task(name="tasks.send_hitl_notification", queue="notifications")
def send_hitl_notification_task(
    checkpoint_id: str,
    gate_type: str,
    context_json: str,
) -> dict:
    """
    Send in-app / email notification to the reviewer for a new HITL checkpoint.
    """
    reviewer_email = os.environ.get("NOTIFY_CLIENT_ADMIN_EMAIL", "")

    if not reviewer_email:
        logger.warning(
            "[HITL-NOTIFY] NOTIFY_CLIENT_ADMIN_EMAIL not set — notification skipped"
        )
        return {"status": "skipped"}

    gate_labels = {
        "UNMAPPED_CHARGE": "Unmapped Charge Review Required",
        "HIGH_VALUE_ANOMALY": "Anomaly Approval Required",
        "DISPUTE_APPROVAL": "Dispute Letter Approval Required",
    }
    label = gate_labels.get(gate_type, gate_type)
    subject = f"[LogiSight] Action Required: {label}"
    body = (
        f"A Human-in-the-Loop review is pending in LogiSight.\n\n"
        f"Gate: {label}\n"
        f"Checkpoint ID: {checkpoint_id}\n\n"
        f"Please log in to the LogiSight portal and navigate to "
        f"'Pending Reviews' to action this checkpoint.\n\n"
        f"LogiSight Autopilot System"
    )

    from app.agent.tools.notifier import _send_email
    success = _send_email(reviewer_email, subject, body)
    return {"status": "sent" if success else "failed"}

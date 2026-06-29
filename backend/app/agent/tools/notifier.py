"""
Autopilot Agent Tool: Notification Dispatcher

Sends email/webhook notifications based on the workflow outcome:
  APPROVED  — notify forwarder and client finance team
  DISPUTED  — send dispute letter to forwarder; notify client
  ESCALATED — alert client admin and super admin
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _send_email(to: str, subject: str, body: str) -> bool:
    """
    Send a plain-text email via SMTP.
    Returns True on success, False on failure.
    """
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass]):
        logger.warning(
            "[NOTIFIER] SMTP not configured "
            "(SMTP_HOST/SMTP_USER/SMTP_PASS not set) — notification skipped"
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, to, msg.as_string())
        logger.info(f"[NOTIFIER] Email sent to {to}: {subject}")
        return True
    except Exception as exc:
        logger.error(f"[NOTIFIER] Email failed to {to}: {exc}")
        return False


@tool
async def tool_send_notifications(
    invoice_id: str,
    outcome: str,
    dispute_letter: str | None = None,
) -> str:
    """
    Send email notifications to relevant parties based on the workflow outcome.

    Args:
        invoice_id: Integer invoice ID.
        outcome: One of "approved" | "disputed" | "escalated".
        dispute_letter: (Optional) The dispute letter text to include when disputed.

    Returns:
        JSON string: {"sent": int, "failed": int, "details": [...]}
    """
    from app.database import async_session_factory
    from app.models import Invoice
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    logger.info(
        f"[TOOL:notifier] Sending '{outcome}' notifications "
        f"for invoice_id={invoice_id}"
    )

    async with async_session_factory() as db:
        inv_result = await db.execute(
            select(Invoice)
            .options(
                selectinload(Invoice.quote).selectinload("forwarder"),
                selectinload(Invoice.quote).selectinload("buyer"),
            )
            .where(Invoice.id == int(invoice_id))
        )
        invoice = inv_result.scalar_one_or_none()

    if not invoice:
        return json.dumps({"error": f"Invoice {invoice_id} not found"})

    quote = invoice.quote
    inv_num = invoice.invoice_number
    client_name = quote.buyer.name if quote and quote.buyer else "Client"
    forwarder_name = quote.forwarder.name if quote and quote.forwarder else "Forwarder"

    sent = 0
    failed = 0
    details = []

    outcome_lower = outcome.lower()

    if outcome_lower == "approved":
        subject = f"[LogiSight] Invoice {inv_num} — Audit Approved"
        body = (
            f"Dear {forwarder_name},\n\n"
            f"Invoice {inv_num} has been successfully audited and approved for payment.\n\n"
            f"Thank you for your continued business.\n\nLogiSight Audit System"
        )
        recipients = [
            os.environ.get("NOTIFY_FORWARDER_EMAIL", ""),
            os.environ.get("NOTIFY_CLIENT_FINANCE_EMAIL", ""),
        ]

    elif outcome_lower == "disputed":
        subject = f"[LogiSight] Invoice {inv_num} — Billing Dispute Notice"
        body = (
            f"Dear Accounts Receivable / Finance,\n\n"
            f"Please find below a formal dispute notice for invoice {inv_num}.\n\n"
            f"{'─' * 60}\n"
            f"{dispute_letter or 'Please refer to the attached dispute details.'}\n"
            f"{'─' * 60}\n\n"
            f"Sent by LogiSight Autopilot Audit System on behalf of {client_name}."
        )
        recipients = [os.environ.get("NOTIFY_FORWARDER_EMAIL", "")]

    elif outcome_lower == "escalated":
        subject = f"[LogiSight] ⚠️ Invoice {inv_num} — Escalation Required"
        body = (
            f"Dear Client Admin,\n\n"
            f"Invoice {inv_num} from {forwarder_name} has been escalated and requires "
            f"your immediate attention in the LogiSight portal.\n\n"
            f"Please review the Pending Reviews section.\n\n"
            f"LogiSight Autopilot System"
        )
        recipients = [
            os.environ.get("NOTIFY_CLIENT_ADMIN_EMAIL", ""),
            os.environ.get("NOTIFY_SUPER_ADMIN_EMAIL", ""),
        ]
    else:
        return json.dumps({"error": f"Unknown outcome: '{outcome}'"})

    for recipient in recipients:
        if recipient:
            success = _send_email(recipient, subject, body)
            if success:
                sent += 1
            else:
                failed += 1
            details.append({"to": recipient, "sent": success})

    logger.info(f"[TOOL:notifier] Done: {sent} sent, {failed} failed")
    return json.dumps({"sent": sent, "failed": failed, "details": details})

"""
Celery application configuration for LogiSight Autopilot Agent.

Queues:
  autopilot   — Autopilot workflow tasks (PDF parsing, mapping, anomaly detection, etc.)
  notifications — Email/webhook notification dispatch tasks

Beat schedule:
  - poll_email_for_invoices: Every 5 minutes (when IMAP configured)
  - escalate_hitl_checkpoints: Every 30 minutes
"""

from __future__ import annotations

import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "logisight",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.autopilot",
        "app.tasks.ingestion",
        "app.tasks.escalation",
    ],
)

# ── Celery configuration ──────────────────────────────────────────────────────
app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_routes={
        "tasks.run_autopilot_workflow": {"queue": "autopilot"},
        "tasks.poll_email_for_invoices": {"queue": "autopilot"},
        "tasks.escalate_hitl_checkpoints": {"queue": "autopilot"},
        "tasks.send_hitl_notification": {"queue": "notifications"},
    },
    # Worker settings
    worker_prefetch_multiplier=1,   # Process one task at a time per worker
    task_acks_late=True,            # Acknowledge after task completes (safer retry)
    task_reject_on_worker_lost=True,
    # Result expiry (24 hours)
    result_expires=86400,
    # Task timeout (10 minutes per workflow run)
    task_soft_time_limit=540,   # 9 min soft limit → triggers SoftTimeLimitExceeded
    task_time_limit=600,        # 10 min hard limit
)

# ── Celery Beat schedule (periodic tasks) ─────────────────────────────────────
app.conf.beat_schedule = {
    "poll-email-every-5-minutes": {
        "task": "tasks.poll_email_for_invoices",
        "schedule": 300.0,  # Every 5 minutes
        "options": {"queue": "autopilot"},
    },
    "escalate-hitl-every-30-minutes": {
        "task": "tasks.escalate_hitl_checkpoints",
        "schedule": 1800.0,  # Every 30 minutes
        "options": {"queue": "autopilot"},
    },
}

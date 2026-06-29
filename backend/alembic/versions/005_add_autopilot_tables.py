"""Add autopilot agent tables: hitl_checkpoints, dispute_letters, audit_records

Revision ID: 005_add_autopilot_tables
Revises: 004_update_basis_constraint
Create Date: 2026-06-29

Tables added:
  - hitl_checkpoints: Human-in-the-Loop review gates for the Autopilot Agent
  - dispute_letters: Qwen-Max generated dispute letter drafts
  - audit_records: Immutable workflow audit trail
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "005_add_autopilot_tables"
down_revision = "004_update_basis_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── HITL enum types ───────────────────────────────────────────────────────
    hitl_gate_type = sa.Enum(
        "UNMAPPED_CHARGE", "HIGH_VALUE_ANOMALY", "DISPUTE_APPROVAL",
        name="hitl_gate_type"
    )
    hitl_status = sa.Enum(
        "PENDING", "APPROVED", "REJECTED", "OVERRIDDEN", "AUTO_ESCALATED",
        name="hitl_status"
    )
    hitl_gate_type.create(op.get_bind(), checkfirst=True)
    hitl_status.create(op.get_bind(), checkfirst=True)

    # ── hitl_checkpoints ──────────────────────────────────────────────────────
    op.create_table(
        "hitl_checkpoints",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("workflow_id", sa.Text(), nullable=False, index=True),
        sa.Column(
            "invoice_id",
            sa.BigInteger(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column(
            "gate_type",
            sa.Enum(
                "UNMAPPED_CHARGE", "HIGH_VALUE_ANOMALY", "DISPUTE_APPROVAL",
                name="hitl_gate_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "APPROVED", "REJECTED", "OVERRIDDEN", "AUTO_ESCALATED",
                name="hitl_status",
                create_type=False,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("context_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("reviewer_id", sa.BigInteger(), nullable=True),
        sa.Column("reviewer_decision", sa.Text(), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalate_after", sa.DateTime(timezone=True), nullable=False),
    )

    # ── dispute_letters ───────────────────────────────────────────────────────
    op.create_table(
        "dispute_letters",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "invoice_id",
            sa.BigInteger(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("letter_text", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="DRAFT"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── audit_records ─────────────────────────────────────────────────────────
    op.create_table(
        "audit_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "invoice_id",
            sa.BigInteger(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workflow_id", sa.Text(), nullable=False, index=True),
        sa.Column("final_status", sa.Text(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_records")
    op.drop_table("dispute_letters")
    op.drop_table("hitl_checkpoints")

    # Drop enum types
    sa.Enum(name="hitl_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="hitl_gate_type").drop(op.get_bind(), checkfirst=True)

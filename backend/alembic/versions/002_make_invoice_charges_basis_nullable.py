"""make invoice_charges basis nullable

Revision ID: 002
Revises: 001
Create Date: 2026-04-18

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make invoice_charges.basis nullable to handle cases where Veryfi cannot determine basis
    op.alter_column(
        "invoice_charges",
        "basis",
        existing_type=sa.Text(),
        nullable=True,
        existing_server_default="Per Shipment",
        server_default=None,
    )


def downgrade() -> None:
    # Revert to NOT NULL with default
    op.alter_column(
        "invoice_charges",
        "basis",
        existing_type=sa.Text(),
        nullable=False,
        server_default="Per Shipment",
    )

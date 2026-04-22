"""make rate and qty nullable in quote_charges and invoice_charges

Revision ID: 003_make_rate_qty_nullable
Revises: 002_make_invoice_charges_basis_nullable
Create Date: 2026-04-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make rate and qty nullable in quote_charges
    op.alter_column('quote_charges', 'rate',
                    existing_type=sa.Numeric(),
                    nullable=True,
                    existing_server_default=sa.text("'0'"))

    op.alter_column('quote_charges', 'qty',
                    existing_type=sa.Numeric(),
                    nullable=True,
                    existing_server_default=sa.text("'1'"))

    # Make rate and qty nullable in invoice_charges
    op.alter_column('invoice_charges', 'rate',
                    existing_type=sa.Numeric(),
                    nullable=True,
                    existing_server_default=sa.text("'0'"))

    op.alter_column('invoice_charges', 'qty',
                    existing_type=sa.Numeric(),
                    nullable=True,
                    existing_server_default=sa.text("'1'"))


def downgrade() -> None:
    # Revert to NOT NULL with defaults
    op.alter_column('invoice_charges', 'qty',
                    existing_type=sa.Numeric(),
                    nullable=False,
                    server_default=sa.text("'1'"))

    op.alter_column('invoice_charges', 'rate',
                    existing_type=sa.Numeric(),
                    nullable=False,
                    server_default=sa.text("'0'"))

    op.alter_column('quote_charges', 'qty',
                    existing_type=sa.Numeric(),
                    nullable=False,
                    server_default=sa.text("'1'"))

    op.alter_column('quote_charges', 'rate',
                    existing_type=sa.Numeric(),
                    nullable=False,
                    server_default=sa.text("'0'"))

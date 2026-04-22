"""update basis check constraint to include Flat Rate and Per Chg Wt

Revision ID: 004
Revises: 003
Create Date: 2026-04-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old check constraints
    op.drop_constraint('ck_quote_charges_basis', 'quote_charges', type_='check')
    op.drop_constraint('ck_invoice_charges_basis', 'invoice_charges', type_='check')

    # Add new check constraints with all 5 basis types
    op.create_check_constraint(
        'ck_quote_charges_basis',
        'quote_charges',
        "basis IN ('Per KG','Per Shipment','Per CBM','Flat Rate','Per Chg Wt')"
    )
    op.create_check_constraint(
        'ck_invoice_charges_basis',
        'invoice_charges',
        "basis IN ('Per KG','Per Shipment','Per CBM','Flat Rate','Per Chg Wt')"
    )


def downgrade() -> None:
    # Revert to old constraints with only 3 basis types
    op.drop_constraint('ck_quote_charges_basis', 'quote_charges', type_='check')
    op.drop_constraint('ck_invoice_charges_basis', 'invoice_charges', type_='check')

    op.create_check_constraint(
        'ck_quote_charges_basis',
        'quote_charges',
        "basis IN ('Per KG','Per Shipment','Per CBM')"
    )
    op.create_check_constraint(
        'ck_invoice_charges_basis',
        'invoice_charges',
        "basis IN ('Per KG','Per Shipment','Per CBM')"
    )

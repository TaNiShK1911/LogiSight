"""Add missing quote columns

Revision ID: c4eebdb0c177
Revises: 005_add_copilot_memory
Create Date: 2026-08-02 22:21:19.045449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c4eebdb0c177'
down_revision: Union[str, None] = '005_add_copilot_memory'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('quotes', sa.Column('etd', sa.Date(), nullable=True))
    op.add_column('quotes', sa.Column('eta', sa.Date(), nullable=True))
    op.add_column('quotes', sa.Column('goods_description', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('quotes', 'goods_description')
    op.drop_column('quotes', 'eta')
    op.drop_column('quotes', 'etd')

"""add activity data fields to transactions

Revision ID: 8d4f2a1e9b50
Revises: 7b9fb3033ae7
Create Date: 2026-04-12 14:00:00.000000

Adds columns to support activity-based emissions calculations:
  - data_type: "spend" or "activity" (default "spend" for all existing rows)
  - activity_type: electricity, gas, diesel, petrol, lpg, heat, water, waste, distance, refrigerants, other
  - quantity: numeric consumption (kWh, litres, m3, kg, km)
  - quantity_unit: the unit the quantity is in
  - raw_activity_label: freeform text when user enters an activity type not in the picker

Existing rows get data_type="spend" via server default. No backfill needed beyond that.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d4f2a1e9b50'
down_revision: Union[str, Sequence[str], None] = '7b9fb3033ae7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'transactions',
        sa.Column('data_type', sa.String(length=20), nullable=False, server_default='spend'),
    )
    op.add_column(
        'transactions',
        sa.Column('activity_type', sa.String(length=50), nullable=True),
    )
    op.add_column(
        'transactions',
        sa.Column('quantity', sa.Float(), nullable=True),
    )
    op.add_column(
        'transactions',
        sa.Column('quantity_unit', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'transactions',
        sa.Column('raw_activity_label', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('transactions', 'raw_activity_label')
    op.drop_column('transactions', 'quantity_unit')
    op.drop_column('transactions', 'quantity')
    op.drop_column('transactions', 'activity_type')
    op.drop_column('transactions', 'data_type')

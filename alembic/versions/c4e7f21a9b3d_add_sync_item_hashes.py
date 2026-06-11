"""add sync_item_hashes table

Revision ID: c4e7f21a9b3d
Revises: e64d985dbe6e
Create Date: 2026-06-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'c4e7f21a9b3d'
down_revision: Union[str, Sequence[str], None] = 'e64d985dbe6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sync_item_hashes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('integration_id', UUID(as_uuid=True), sa.ForeignKey('sis_integrations.id'), nullable=False),
        sa.Column('item_key', sa.Text(), nullable=False),
        sa.Column('props_hash', sa.Text(), nullable=False),
        sa.UniqueConstraint('integration_id', 'item_key', name='uq_sync_item_hashes'),
    )
    op.create_index('ix_sync_item_hashes_integration', 'sync_item_hashes', ['integration_id'])


def downgrade() -> None:
    op.drop_index('ix_sync_item_hashes_integration', table_name='sync_item_hashes')
    op.drop_table('sync_item_hashes')

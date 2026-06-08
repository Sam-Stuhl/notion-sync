"""rename external_integrations to sis_integrations

Revision ID: e64d985dbe6e
Revises: 85f1cd1ec781
Create Date: 2026-06-08 09:08:21.600555

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e64d985dbe6e'
down_revision: Union[str, Sequence[str], None] = '85f1cd1ec781'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("external_integrations", "sis_integrations")
    op.alter_column("sync_runs", "external_integration_id", new_column_name="sis_integration_id")


def downgrade() -> None:
    op.alter_column("sync_runs", "sis_integration_id", new_column_name="external_integration_id")
    op.rename_table("sis_integrations", "external_integrations")

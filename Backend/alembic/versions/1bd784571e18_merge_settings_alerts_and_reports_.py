"""merge settings_alerts and reports branches

Revision ID: 1bd784571e18
Revises: 0003c1d2e3f4, 81c942de352a
Create Date: 2026-08-27 22:41:29.088646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1bd784571e18'
down_revision: Union[str, Sequence[str], None] = ('0003c1d2e3f4', '81c942de352a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

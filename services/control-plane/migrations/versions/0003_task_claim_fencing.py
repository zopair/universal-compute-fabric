"""Add hashed worker claim fencing tokens."""

from alembic import op
import sqlalchemy as sa

revision = "0003_task_claim_fencing"
down_revision = "0002_tasks_and_reservations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("claim_token_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "claim_token_hash")

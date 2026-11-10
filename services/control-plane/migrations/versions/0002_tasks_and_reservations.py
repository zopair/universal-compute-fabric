"""Add task lifecycle and resource reservations."""

from alembic import op
import sqlalchemy as sa

revision = "0002_tasks_and_reservations"
down_revision = "0001_initial_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("task_id", sa.String(length=128), primary_key=True),
        sa.Column("assigned_node_id", sa.String(length=128), sa.ForeignKey("compute_nodes.node_id"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("image", sa.String(length=320), nullable=False),
        sa.Column("command", sa.JSON(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("cpu_millicores", sa.Integer(), nullable=False),
        sa.Column("memory_mb", sa.Integer(), nullable=False),
        sa.Column("gpu_units", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_tasks_assigned_node_id", "tasks", ["assigned_node_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_table(
        "resource_reservations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(length=128), sa.ForeignKey("tasks.task_id"), nullable=False, unique=True),
        sa.Column("node_id", sa.String(length=128), sa.ForeignKey("compute_nodes.node_id"), nullable=False),
        sa.Column("cpu_millicores", sa.Integer(), nullable=False),
        sa.Column("memory_mb", sa.Integer(), nullable=False),
        sa.Column("gpu_units", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_resource_reservations_node_id", "resource_reservations", ["node_id"])
    op.create_index("ix_resource_reservations_status", "resource_reservations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_resource_reservations_status", table_name="resource_reservations")
    op.drop_index("ix_resource_reservations_node_id", table_name="resource_reservations")
    op.drop_table("resource_reservations")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_assigned_node_id", table_name="tasks")
    op.drop_table("tasks")

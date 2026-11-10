"""Initial persistent node registry and audit log."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_registry"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compute_nodes",
        sa.Column("node_id", sa.String(length=128), primary_key=True),
        sa.Column("tier", sa.String(length=16), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("cpu_millicores", sa.Integer(), nullable=False),
        sa.Column("memory_mb", sa.Integer(), nullable=False),
        sa.Column("available_cpu_millicores", sa.Integer(), nullable=True),
        sa.Column("available_memory_mb", sa.Integer(), nullable=True),
        sa.Column("gpu_units", sa.Integer(), nullable=False),
        sa.Column("estimated_latency_ms", sa.Float(), nullable=False),
        sa.Column("estimated_cost_per_minute", sa.Float(), nullable=False),
        sa.Column("trust_level", sa.Integer(), nullable=False),
        sa.Column("labels", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("credential_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_compute_nodes_tier", "compute_nodes", ["tier"])
    op.create_index("ix_compute_nodes_region", "compute_nodes", ["region"])
    op.create_index("ix_compute_nodes_status", "compute_nodes", ["status"])
    op.create_index("ix_compute_nodes_lease_expires_at", "compute_nodes", ["lease_expires_at"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=128), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_subject_id", "audit_events", ["subject_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_subject_id", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_compute_nodes_lease_expires_at", table_name="compute_nodes")
    op.drop_index("ix_compute_nodes_status", table_name="compute_nodes")
    op.drop_index("ix_compute_nodes_region", table_name="compute_nodes")
    op.drop_index("ix_compute_nodes_tier", table_name="compute_nodes")
    op.drop_table("compute_nodes")

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ucf.config import settings
from ucf.entities import AuditEvent, NodeRecord
from ucf.models import ComputeNode, HeartbeatRequest, NodeStatusResponse
from ucf.security import create_node_token, hash_token


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def node_to_model(record: NodeRecord) -> ComputeNode:
    return ComputeNode(
        node_id=record.node_id,
        tier=record.tier,
        region=record.region,
        capabilities=set(record.capabilities or []),
        cpu_millicores=record.cpu_millicores,
        memory_mb=record.memory_mb,
        gpu_units=record.gpu_units,
        estimated_latency_ms=record.estimated_latency_ms,
        estimated_cost_per_minute=record.estimated_cost_per_minute,
        trust_level=record.trust_level,
        labels=record.labels or {},
    )


def add_audit(db: Session, event_type: str, subject_id: str, detail: str = "") -> None:
    db.add(AuditEvent(event_type=event_type, subject_id=subject_id, detail=detail, created_at=utcnow()))


def enroll_node(db: Session, node: ComputeNode) -> tuple[NodeRecord, str | None]:
    now = utcnow()
    record = db.get(NodeRecord, node.node_id)
    token: str | None = None
    if record is None:
        token = create_node_token()
        record = NodeRecord(
            node_id=node.node_id,
            credential_hash=hash_token(token),
            created_at=now,
            last_seen_at=now,
            lease_expires_at=now + timedelta(seconds=settings.node_lease_seconds),
            status="active",
        )
        db.add(record)
        add_audit(db, "node.enrolled", node.node_id)
    else:
        record.status = "active"
        record.last_seen_at = now
        record.lease_expires_at = now + timedelta(seconds=settings.node_lease_seconds)
        record.updated_at = now
        add_audit(db, "node.inventory_updated", node.node_id)

    record.tier = node.tier.value
    record.region = node.region
    record.capabilities = sorted(node.capabilities)
    record.cpu_millicores = node.cpu_millicores
    record.memory_mb = node.memory_mb
    record.gpu_units = node.gpu_units
    record.estimated_latency_ms = node.estimated_latency_ms
    record.estimated_cost_per_minute = node.estimated_cost_per_minute
    record.trust_level = node.trust_level
    record.labels = node.labels
    record.updated_at = now
    db.commit()
    db.refresh(record)
    return record, token


def refresh_heartbeat(db: Session, record: NodeRecord, heartbeat: HeartbeatRequest) -> NodeRecord:
    now = utcnow()
    for field in ("cpu_millicores", "memory_mb", "gpu_units", "estimated_latency_ms"):
        value = getattr(heartbeat, field)
        if value is not None:
            setattr(record, field, value)
    if heartbeat.capabilities is not None:
        record.capabilities = sorted(heartbeat.capabilities)
    record.last_seen_at = now
    record.lease_expires_at = now + timedelta(seconds=settings.node_lease_seconds)
    record.status = "active"
    record.updated_at = now
    db.commit()
    db.refresh(record)
    return record


def expire_stale_nodes(db: Session) -> int:
    now = utcnow()
    expired = list(
        db.execute(
            select(NodeRecord).where(
                NodeRecord.status == "active",
                NodeRecord.lease_expires_at.is_not(None),
                NodeRecord.lease_expires_at < now,
            )
        ).scalars()
    )
    for record in expired:
        record.status = "stale"
        record.updated_at = now
        add_audit(db, "node.lease_expired", record.node_id)
    if expired:
        db.commit()
    return len(expired)


def list_node_status(db: Session, include_stale: bool = False) -> list[NodeStatusResponse]:
    expire_stale_nodes(db)
    query = select(NodeRecord)
    if not include_stale:
        query = query.where(NodeRecord.status == "active")
    records = db.execute(query.order_by(NodeRecord.node_id)).scalars().all()
    return [
        NodeStatusResponse(
            node=node_to_model(record),
            status=record.status,
            last_seen_at=record.last_seen_at,
            lease_expires_at=record.lease_expires_at,
        )
        for record in records
    ]


def get_schedulable_nodes(db: Session) -> list[ComputeNode]:
    expire_stale_nodes(db)
    records = db.execute(
        select(NodeRecord).where(
            NodeRecord.status == "active",
            NodeRecord.lease_expires_at > utcnow(),
        )
    ).scalars().all()
    return [node_to_model(record) for record in records]


def delete_node(db: Session, node_id: str) -> bool:
    record = db.get(NodeRecord, node_id)
    if record is None:
        return False
    add_audit(db, "node.deleted", node_id)
    db.delete(record)
    db.commit()
    return True



def rotate_node_token(db: Session, node_id: str) -> str | None:
    record = db.get(NodeRecord, node_id)
    if record is None:
        return None
    token = create_node_token()
    record.credential_hash = hash_token(token)
    record.updated_at = utcnow()
    add_audit(db, "node.credential_rotated", node_id)
    db.commit()
    return token

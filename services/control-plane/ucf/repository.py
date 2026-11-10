from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ucf.config import settings
from ucf.entities import AuditEvent, NodeRecord, ResourceReservation, TaskRecord
from ucf.models import ComputeNode, HeartbeatRequest, NodeStatusResponse, TaskCreateRequest, TaskResponse
from ucf.security import create_node_token, hash_token


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def node_to_model(record: NodeRecord) -> ComputeNode:
    return ComputeNode(
        node_id=record.node_id, tier=record.tier, region=record.region,
        capabilities=set(record.capabilities or []), cpu_millicores=record.cpu_millicores,
        memory_mb=record.memory_mb, available_cpu_millicores=record.available_cpu_millicores,
        available_memory_mb=record.available_memory_mb, gpu_units=record.gpu_units,
        estimated_latency_ms=record.estimated_latency_ms,
        estimated_cost_per_minute=record.estimated_cost_per_minute,
        trust_level=record.trust_level, labels=record.labels or {},
    )


def task_to_model(record: TaskRecord) -> TaskResponse:
    return TaskResponse(
        task_id=record.task_id, status=record.status, assigned_node_id=record.assigned_node_id,
        image=record.image, command=record.command, timeout_seconds=record.timeout_seconds,
        cpu_millicores=record.cpu_millicores, memory_mb=record.memory_mb, gpu_units=record.gpu_units,
        created_at=record.created_at, started_at=record.started_at,
        completed_at=record.completed_at, exit_code=record.exit_code,
        result=record.result, error=record.error,
    )


def add_audit(db: Session, event_type: str, subject_id: str, detail: str = "") -> None:
    db.add(AuditEvent(event_type=event_type, subject_id=subject_id, detail=detail, created_at=utcnow()))


def active_reservations(db: Session, node_id: str) -> tuple[int, int, int]:
    row = db.execute(
        select(
            func.coalesce(func.sum(ResourceReservation.cpu_millicores), 0),
            func.coalesce(func.sum(ResourceReservation.memory_mb), 0),
            func.coalesce(func.sum(ResourceReservation.gpu_units), 0),
        ).where(ResourceReservation.node_id == node_id, ResourceReservation.status == "active")
    ).one()
    return int(row[0]), int(row[1]), int(row[2])


def effective_node_model(db: Session, record: NodeRecord) -> ComputeNode:
    node = node_to_model(record)
    reserved_cpu, reserved_memory, reserved_gpu = active_reservations(db, record.node_id)
    if node.available_cpu_millicores is not None:
        node.available_cpu_millicores = max(0, node.available_cpu_millicores - reserved_cpu)
    if node.available_memory_mb is not None:
        node.available_memory_mb = max(0, node.available_memory_mb - reserved_memory)
    node.gpu_units = max(0, node.gpu_units - reserved_gpu)
    return node


def enroll_node(db: Session, node: ComputeNode) -> tuple[NodeRecord, str | None]:
    now = utcnow()
    record = db.get(NodeRecord, node.node_id)
    token: str | None = None
    if record is None:
        token = create_node_token()
        record = NodeRecord(
            node_id=node.node_id, credential_hash=hash_token(token), created_at=now,
            last_seen_at=None, lease_expires_at=None, status="pending",
        )
        db.add(record)
        add_audit(db, "node.enrolled", node.node_id)
    else:
        record.status = "pending"
        record.last_seen_at = None
        record.lease_expires_at = None
        record.available_cpu_millicores = None
        record.available_memory_mb = None
        record.updated_at = now
        add_audit(db, "node.inventory_updated", node.node_id)

    record.tier = node.tier.value
    record.region = node.region
    record.capabilities = sorted(node.capabilities)
    record.cpu_millicores = node.cpu_millicores
    record.memory_mb = node.memory_mb
    record.available_cpu_millicores = node.available_cpu_millicores
    record.available_memory_mb = node.available_memory_mb
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
    for field in ("available_cpu_millicores", "available_memory_mb", "gpu_units", "estimated_latency_ms"):
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
    expired = list(db.execute(select(NodeRecord).where(
        NodeRecord.status == "active", NodeRecord.lease_expires_at.is_not(None),
        NodeRecord.lease_expires_at < now,
    )).scalars())
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
            node=effective_node_model(db, record), status=record.status,
            last_seen_at=record.last_seen_at, lease_expires_at=record.lease_expires_at,
        ) for record in records
    ]


def get_schedulable_nodes(db: Session) -> list[ComputeNode]:
    expire_stale_nodes(db)
    records = db.execute(select(NodeRecord).where(
        NodeRecord.status == "active", NodeRecord.lease_expires_at > utcnow(),
    )).scalars().all()
    return [effective_node_model(db, record) for record in records]


def create_task_with_reservation(db: Session, payload: TaskCreateRequest, node_id: str) -> TaskRecord:
    now = utcnow()
    workload = payload.workload
    record = db.execute(
        select(NodeRecord).where(NodeRecord.node_id == node_id).with_for_update()
    ).scalar_one_or_none()
    if record is None or record.status != "active" or not record.lease_expires_at or record.lease_expires_at <= now:
        raise ValueError("Selected node is no longer active")
    effective = effective_node_model(db, record)
    available_cpu = effective.available_cpu_millicores
    available_memory = effective.available_memory_mb
    if available_cpu is None or available_memory is None:
        raise ValueError("Node has not reported live CPU and memory availability")
    if (available_cpu < workload.cpu_millicores or available_memory < workload.memory_mb
            or effective.gpu_units < workload.gpu_units):
        raise ValueError("Node capacity changed before reservation; retry placement")
    if db.get(TaskRecord, workload.workload_id) is not None:
        raise ValueError("workload_id already exists")
    task = TaskRecord(
        task_id=workload.workload_id, assigned_node_id=node_id, status="pending",
        image=payload.image, command=payload.command, timeout_seconds=payload.timeout_seconds,
        cpu_millicores=workload.cpu_millicores, memory_mb=workload.memory_mb,
        gpu_units=workload.gpu_units, created_at=now,
    )
    db.add(task)
    db.flush()
    db.add(ResourceReservation(
        task_id=task.task_id, node_id=node_id, cpu_millicores=workload.cpu_millicores,
        memory_mb=workload.memory_mb, gpu_units=workload.gpu_units, status="active",
        created_at=now,
    ))
    add_audit(db, "task.queued", task.task_id, f"node={node_id}")
    db.commit()
    db.refresh(task)
    return task


def claim_next_task(db: Session, node_id: str) -> TaskRecord | None:
    now = utcnow()
    expired_claims = db.execute(select(TaskRecord).where(
        TaskRecord.assigned_node_id == node_id, TaskRecord.status == "running",
        TaskRecord.claim_expires_at.is_not(None), TaskRecord.claim_expires_at <= now,
    ).with_for_update()).scalars().all()
    for expired in expired_claims:
        expired.status = "pending"
        expired.started_at = None
        expired.claim_expires_at = None
        add_audit(db, "task.claim_expired", expired.task_id, f"node={node_id}")
    if expired_claims:
        db.flush()
    task = db.execute(select(TaskRecord).where(
        TaskRecord.assigned_node_id == node_id, TaskRecord.status == "pending",
    ).order_by(TaskRecord.created_at, TaskRecord.task_id).with_for_update(skip_locked=True)).scalars().first()
    if task is None:
        return None
    task.status = "running"
    task.started_at = now
    task.claim_expires_at = now + timedelta(seconds=task.timeout_seconds + 30)
    add_audit(db, "task.started", task.task_id, f"node={node_id}")
    db.commit()
    db.refresh(task)
    return task


def complete_task(db: Session, task_id: str, node_id: str, status: str,
                  exit_code: int, result: str | None, error: str | None) -> TaskRecord:
    task = db.execute(select(TaskRecord).where(
        TaskRecord.task_id == task_id, TaskRecord.assigned_node_id == node_id,
    ).with_for_update()).scalar_one_or_none()
    if task is None:
        raise LookupError("Task not found for this node")
    if task.status != "running":
        raise ValueError(f"Task cannot transition from {task.status} to {status}")
    if (status == "succeeded" and exit_code != 0) or (status == "failed" and exit_code == 0):
        raise ValueError("Task status and exit code are inconsistent")
    now = utcnow()
    task.status = status
    task.exit_code = exit_code
    task.result = result
    task.error = error
    task.completed_at = now
    task.claim_expires_at = None
    reservation = db.execute(select(ResourceReservation).where(
        ResourceReservation.task_id == task_id, ResourceReservation.status == "active",
    ).with_for_update()).scalar_one_or_none()
    if reservation is not None:
        reservation.status = "released"
        reservation.released_at = now
    add_audit(db, f"task.{status}", task_id, f"node={node_id};exit_code={exit_code}")
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: str) -> TaskRecord | None:
    return db.get(TaskRecord, task_id)


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
    record.status = "pending"
    record.last_seen_at = None
    record.lease_expires_at = None
    record.available_cpu_millicores = None
    record.available_memory_mb = None
    record.updated_at = utcnow()
    add_audit(db, "node.credential_rotated", node_id)
    db.commit()
    return token

from __future__ import annotations

from datetime import timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ucf.config import settings
from ucf.database import get_db
from ucf.models import (
    ComputeNode, HeartbeatRequest, HeartbeatResponse, NodeEnrollmentResponse,
    NodeStatusResponse, TaskClaimResponse, TaskCompletionRequest, TaskCreateRequest,
    TaskResponse, WorkloadRequest,
)
from ucf.observability import instrument
from ucf.repository import (
    claim_next_task, complete_task, create_task_with_reservation, delete_node,
    enroll_node, get_schedulable_nodes, get_task, list_node_status, node_to_model,
    refresh_heartbeat, rotate_node_token, task_to_model, utcnow,
)
from ucf.scheduler import schedule
from ucf.security import require_admin, require_node

app = FastAPI(
    title="Universal Compute Fabric Control Plane",
    version="0.3.0",
    description="Hybrid compute placement, task dispatch and resource reservation control plane.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ucf-control-plane", "stage": "m2"}


@app.get("/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready", "database": "ok"}


@app.put("/v1/nodes/{node_id}", response_model=NodeEnrollmentResponse, dependencies=[Depends(require_admin)])
def upsert_node(node_id: str, node: ComputeNode, db: Session = Depends(get_db)):
    if node_id != node.node_id:
        raise HTTPException(status_code=400, detail="Path node_id must match body node_id")
    record, token = enroll_node(db, node)
    return NodeEnrollmentResponse(
        node=node_to_model(record), node_token=token, lease_seconds=settings.node_lease_seconds,
        credential_note=("Store this token securely; it is returned only on first enrollment."
                         if token else "Existing node credential retained; token is not returned again."),
    )


@app.get("/v1/nodes", response_model=list[NodeStatusResponse], dependencies=[Depends(require_admin)])
def list_nodes(include_stale: bool = Query(default=False), db: Session = Depends(get_db)):
    return list_node_status(db, include_stale=include_stale)


@app.post("/v1/nodes/{node_id}/heartbeat", response_model=HeartbeatResponse)
def heartbeat(node_id: str, payload: HeartbeatRequest, record=Depends(require_node),
              db: Session = Depends(get_db)):
    if record.node_id != node_id:
        raise HTTPException(status_code=403, detail="Credential does not belong to this node")
    updated = refresh_heartbeat(db, record, payload)
    expires = updated.lease_expires_at
    if expires is None:
        raise HTTPException(status_code=500, detail="Lease was not created")
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return HeartbeatResponse(
        node_id=updated.node_id, status=updated.status, server_time=utcnow(),
        lease_expires_at=expires, lease_seconds=settings.node_lease_seconds,
    )


@app.post("/v1/nodes/{node_id}/rotate-token", dependencies=[Depends(require_admin)])
def rotate_token(node_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    token = rotate_node_token(db, node_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"node_id": node_id, "node_token": token}


@app.delete("/v1/nodes/{node_id}", dependencies=[Depends(require_admin)])
def remove_node(node_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    if not delete_node(db, node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    return {"status": "deleted", "node_id": node_id}


@app.post("/v1/schedule", dependencies=[Depends(require_admin)])
def propose_placement(job: WorkloadRequest, db: Session = Depends(get_db)):
    decision = schedule(job, get_schedulable_nodes(db))
    if decision.status == "no_eligible_node":
        raise HTTPException(status_code=409, detail=decision.model_dump(mode="json"))
    return decision


@app.post("/v1/tasks", response_model=TaskResponse, status_code=202,
          dependencies=[Depends(require_admin)])
def submit_task(payload: TaskCreateRequest, db: Session = Depends(get_db)):
    decision = schedule(payload.workload, get_schedulable_nodes(db))
    if decision.status == "no_eligible_node" or decision.selected_node is None:
        raise HTTPException(status_code=409, detail=decision.model_dump(mode="json"))
    try:
        task = create_task_with_reservation(db, payload, decision.selected_node.node_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return task_to_model(task)


@app.get("/v1/tasks/{task_id}", response_model=TaskResponse,
         dependencies=[Depends(require_admin)])
def read_task(task_id: str, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_model(task)


@app.post("/v1/worker/tasks/claim", response_model=TaskClaimResponse)
def worker_claim(record=Depends(require_node), db: Session = Depends(get_db)):
    task = claim_next_task(db, record.node_id)
    return TaskClaimResponse(task=task_to_model(task) if task else None)


@app.post("/v1/worker/tasks/{task_id}/complete", response_model=TaskResponse)
def worker_complete(task_id: str, payload: TaskCompletionRequest,
                    record=Depends(require_node), db: Session = Depends(get_db)):
    try:
        task = complete_task(db, task_id, record.node_id, payload.status,
                             payload.exit_code, payload.result, payload.error)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return task_to_model(task)


instrument(app)

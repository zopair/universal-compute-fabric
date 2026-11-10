from datetime import datetime, timedelta, timezone

from ucf.database import get_db
from ucf.entities import NodeRecord, TaskRecord
from ucf.main import app


def node_payload(node_id="edge-1"):
    return {
        "node_id": node_id, "tier": "edge", "region": "eg-cairo",
        "capabilities": ["cpu", "gpu"], "cpu_millicores": 8000,
        "memory_mb": 16384, "gpu_units": 1, "estimated_latency_ms": 15,
        "estimated_cost_per_minute": 0.02, "trust_level": 2, "labels": {},
    }


def enroll_active_node(client, node_id="edge-1"):
    headers = {"X-UCF-Admin-Key": "test-admin-key"}
    enrolled = client.put(f"/v1/nodes/{node_id}", json=node_payload(node_id), headers=headers)
    token = enrolled.json()["node_token"]
    heartbeat = client.post(
        f"/v1/nodes/{node_id}/heartbeat",
        json={"available_cpu_millicores": 7000, "available_memory_mb": 12000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert heartbeat.status_code == 200
    return headers, token


def db_session():
    return app.dependency_overrides[get_db]()


def test_health_and_readiness(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["status"] == "ready"


def test_admin_authentication_required(client):
    response = client.put("/v1/nodes/edge-1", json=node_payload(),
                          headers={"X-UCF-Admin-Key": "wrong"})
    assert response.status_code == 401


def test_enroll_heartbeat_and_node_scoped_credential(client):
    headers = {"X-UCF-Admin-Key": "test-admin-key"}
    enrolled = client.put("/v1/nodes/edge-1", json=node_payload(), headers=headers)
    assert enrolled.status_code == 200
    token = enrolled.json()["node_token"]
    assert token
    beat = client.post("/v1/nodes/edge-1/heartbeat",
                       json={"available_cpu_millicores": 6000, "available_memory_mb": 4096},
                       headers={"Authorization": f"Bearer {token}"})
    assert beat.status_code == 200
    assert beat.json()["status"] == "active"
    assert beat.json()["lease_seconds"] == 45
    wrong_node = client.post("/v1/nodes/other/heartbeat", json={},
                             headers={"Authorization": f"Bearer {token}"})
    assert wrong_node.status_code == 403
    again = client.put("/v1/nodes/edge-1", json=node_payload(), headers=headers)
    assert again.status_code == 200
    assert again.json()["node_token"] is None


def test_stale_node_is_not_scheduled(client):
    headers, _token = enroll_active_node(client)
    db_generator = db_session()
    db = next(db_generator)
    try:
        record = db.get(NodeRecord, "edge-1")
        record.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db.commit()
    finally:
        db.close()
        db_generator.close()
    job = {
        "workload_id": "job-stale", "required_capabilities": ["gpu"],
        "cpu_millicores": 1000, "memory_mb": 512, "gpu_units": 1,
        "max_latency_ms": 80, "minimum_trust_level": 1, "allowed_tiers": ["edge"],
    }
    response = client.post("/v1/schedule", json=job, headers=headers)
    assert response.status_code == 409
    nodes = client.get("/v1/nodes?include_stale=true", headers=headers).json()
    assert nodes[0]["status"] == "stale"


def test_schedule_uses_persisted_live_inventory(client):
    headers, _ = enroll_active_node(client)
    job = {
        "workload_id": "job-1", "required_capabilities": ["gpu"],
        "cpu_millicores": 1000, "memory_mb": 512, "gpu_units": 1,
        "max_latency_ms": 80, "minimum_trust_level": 1,
        "allowed_tiers": ["edge"], "preferred_tier": "edge",
    }
    response = client.post("/v1/schedule", json=job, headers=headers)
    assert response.status_code == 200
    assert response.json()["selected_node"]["node_id"] == "edge-1"


def task_payload(task_id="task-1", cpu=2000, memory=2048):
    return {
        "workload": {
            "workload_id": task_id, "required_capabilities": ["cpu"],
            "cpu_millicores": cpu, "memory_mb": memory, "gpu_units": 0,
            "max_latency_ms": 80, "minimum_trust_level": 1, "allowed_tiers": ["edge"],
        },
        "image": "ghcr.io/example/worker@sha256:" + "a" * 64,
        "command": ["python", "-c", "print('ucf')"],
        "timeout_seconds": 20,
    }


def test_task_submission_reserves_capacity_and_worker_claims(client):
    admin, token = enroll_active_node(client)
    created = client.post("/v1/tasks", json=task_payload(), headers=admin)
    assert created.status_code == 202
    assert created.json()["status"] == "pending"
    assert created.json()["assigned_node_id"] == "edge-1"

    nodes = client.get("/v1/nodes", headers=admin).json()
    assert nodes[0]["node"]["available_cpu_millicores"] == 5000
    assert nodes[0]["node"]["available_memory_mb"] == 9952

    claim = client.post("/v1/worker/tasks/claim", headers={"Authorization": f"Bearer {token}"})
    assert claim.status_code == 200
    assert claim.json()["task"]["status"] == "running"
    assert claim.json()["task"]["command"] == ["python", "-c", "print('ucf')"]
    assert claim.json()["task"]["cpu_millicores"] == 2000
    assert claim.json()["task"]["memory_mb"] == 2048
    assert isinstance(claim.json()["claim_token"], str)
    assert len(claim.json()["claim_token"]) >= 32


def test_task_completion_releases_capacity_and_is_node_scoped(client):
    admin, token = enroll_active_node(client)
    assert client.post("/v1/tasks", json=task_payload(), headers=admin).status_code == 202
    claim = client.post("/v1/worker/tasks/claim", headers={"Authorization": f"Bearer {token}"})
    task_id = claim.json()["task"]["task_id"]
    claim_token = claim.json()["claim_token"]
    wrong = client.post(f"/v1/worker/tasks/{task_id}/complete",
                        json={"claim_token": claim_token, "status": "succeeded", "exit_code": 0, "result": "ok"},
                        headers={"Authorization": "Bearer another-node-token"})
    assert wrong.status_code == 401
    done = client.post(f"/v1/worker/tasks/{task_id}/complete",
                       json={"claim_token": claim_token, "status": "succeeded", "exit_code": 0, "result": "ok"},
                       headers={"Authorization": f"Bearer {token}"})
    assert done.status_code == 200
    assert done.json()["status"] == "succeeded"
    nodes = client.get("/v1/nodes", headers=admin).json()
    assert nodes[0]["node"]["available_cpu_millicores"] == 7000
    assert nodes[0]["node"]["available_memory_mb"] == 12000
    duplicate = client.post(f"/v1/worker/tasks/{task_id}/complete",
                            json={"claim_token": claim_token, "status": "succeeded", "exit_code": 0},
                            headers={"Authorization": f"Bearer {token}"})
    assert duplicate.status_code == 409


def test_task_capacity_is_reserved_against_overcommit(client):
    admin, _ = enroll_active_node(client)
    first = client.post("/v1/tasks", json=task_payload("first", cpu=5000), headers=admin)
    second = client.post("/v1/tasks", json=task_payload("second", cpu=3000), headers=admin)
    assert first.status_code == 202
    assert second.status_code == 409


def test_task_image_must_be_digest_pinned(client):
    admin, _ = enroll_active_node(client)
    payload = task_payload()
    payload["image"] = "python:3.12"
    assert client.post("/v1/tasks", json=payload, headers=admin).status_code == 422


def test_invalid_node_token_rejected(client):
    response = client.post("/v1/nodes/edge-1/heartbeat", json={},
                           headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401


def test_admin_rotation_invalidates_previous_node_token(client):
    admin = {"X-UCF-Admin-Key": "test-admin-key"}
    enrolled = client.put("/v1/nodes/edge-1", json=node_payload(), headers=admin)
    old_token = enrolled.json()["node_token"]
    rotated = client.post("/v1/nodes/edge-1/rotate-token", headers=admin)
    assert rotated.status_code == 200
    new_token = rotated.json()["node_token"]
    assert new_token != old_token
    assert client.get("/v1/nodes", headers=admin).json() == []
    old_heartbeat = client.post("/v1/nodes/edge-1/heartbeat", json={},
                                headers={"Authorization": f"Bearer {old_token}"})
    new_heartbeat = client.post(
        "/v1/nodes/edge-1/heartbeat",
        json={"available_cpu_millicores": 7000, "available_memory_mb": 12000},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert old_heartbeat.status_code == 401
    assert new_heartbeat.status_code == 200


def test_node_identifier_rejects_path_unsafe_characters(client):
    response = client.put("/v1/nodes/bad@id", json=node_payload("bad@id"),
                          headers={"X-UCF-Admin-Key": "test-admin-key"})
    assert response.status_code == 422


def test_pending_node_is_not_schedulable_before_heartbeat(client):
    headers = {"X-UCF-Admin-Key": "test-admin-key"}
    client.put("/v1/nodes/edge-1", json=node_payload(), headers=headers)
    response = client.post("/v1/schedule", json={"workload_id": "early-job"}, headers=headers)
    assert response.status_code == 409



def test_expired_worker_claim_is_requeued_without_releasing_reservation(client):
    admin, token = enroll_active_node(client)
    assert client.post("/v1/tasks", json=task_payload(), headers=admin).status_code == 202
    first = client.post("/v1/worker/tasks/claim", headers={"Authorization": f"Bearer {token}"})
    assert first.json()["task"]["status"] == "running"
    first_claim_token = first.json()["claim_token"]

    generator = db_session()
    db = next(generator)
    try:
        task = db.get(TaskRecord, "task-1")
        task.claim_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()
        generator.close()

    expired_completion = client.post(
        "/v1/worker/tasks/task-1/complete",
        json={"claim_token": first_claim_token, "status": "succeeded", "exit_code": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert expired_completion.status_code == 409

    second = client.post("/v1/worker/tasks/claim", headers={"Authorization": f"Bearer {token}"})
    assert second.status_code == 200
    assert second.json()["task"]["status"] == "running"
    assert second.json()["task"]["task_id"] == "task-1"
    second_claim_token = second.json()["claim_token"]
    assert second_claim_token != first_claim_token
    stale_completion = client.post(
        "/v1/worker/tasks/task-1/complete",
        json={"claim_token": first_claim_token, "status": "succeeded", "exit_code": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert stale_completion.status_code == 409
    nodes_while_requeued = client.get("/v1/nodes", headers=admin).json()
    assert nodes_while_requeued[0]["node"]["available_cpu_millicores"] == 5000
    valid_completion = client.post(
        "/v1/worker/tasks/task-1/complete",
        json={"claim_token": second_claim_token, "status": "succeeded", "exit_code": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert valid_completion.status_code == 200
    nodes_after_completion = client.get("/v1/nodes", headers=admin).json()
    assert nodes_after_completion[0]["node"]["available_cpu_millicores"] == 7000



def test_node_with_task_history_cannot_be_deleted(client):
    admin, _ = enroll_active_node(client)
    assert client.post("/v1/tasks", json=task_payload(), headers=admin).status_code == 202
    response = client.delete("/v1/nodes/edge-1", headers=admin)
    assert response.status_code == 409
    assert "task history" in response.json()["detail"]



def test_gpu_task_is_rejected_until_gpu_runtime_exists(client):
    admin, _ = enroll_active_node(client)
    payload = task_payload()
    payload["workload"]["gpu_units"] = 1
    response = client.post("/v1/tasks", json=payload, headers=admin)
    assert response.status_code == 422
    assert "GPU tasks are not supported" in str(response.json())

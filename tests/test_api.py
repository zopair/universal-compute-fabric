from datetime import datetime, timedelta, timezone

from ucf.database import get_db
from ucf.entities import NodeRecord
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
    headers, token = enroll_active_node(client)
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


def test_task_completion_releases_capacity_and_is_node_scoped(client):
    admin, token = enroll_active_node(client)
    assert client.post("/v1/tasks", json=task_payload(), headers=admin).status_code == 202
    claim = client.post("/v1/worker/tasks/claim", headers={"Authorization": f"Bearer {token}"})
    task_id = claim.json()["task"]["task_id"]
    wrong = client.post(f"/v1/worker/tasks/{task_id}/complete",
                        json={"status": "succeeded", "exit_code": 0, "result": "ok"},
                        headers={"Authorization": "Bearer another-node-token"})
    assert wrong.status_code == 401
    done = client.post(f"/v1/worker/tasks/{task_id}/complete",
                       json={"status": "succeeded", "exit_code": 0, "result": "ok"},
                       headers={"Authorization": f"Bearer {token}"})
    assert done.status_code == 200
    assert done.json()["status"] == "succeeded"
    nodes = client.get("/v1/nodes", headers=admin).json()
    assert nodes[0]["node"]["available_cpu_millicores"] == 7000
    assert nodes[0]["node"]["available_memory_mb"] == 12000
    duplicate = client.post(f"/v1/worker/tasks/{task_id}/complete",
                            json={"status": "succeeded", "exit_code": 0},
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

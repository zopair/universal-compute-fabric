from datetime import datetime, timedelta, timezone

from ucf.database import get_db
from ucf.entities import NodeRecord
from ucf.main import app


def node_payload(node_id="edge-1"):
    return {
        "node_id": node_id,
        "tier": "edge",
        "region": "eg-cairo",
        "capabilities": ["cpu", "gpu"],
        "cpu_millicores": 8000,
        "memory_mb": 16384,
        "gpu_units": 1,
        "estimated_latency_ms": 15,
        "estimated_cost_per_minute": 0.02,
        "trust_level": 2,
        "labels": {},
    }


def test_health_and_readiness(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["status"] == "ready"


def test_admin_authentication_required(client):
    response = client.put("/v1/nodes/edge-1", json=node_payload(), headers={"X-UCF-Admin-Key": "wrong"})
    assert response.status_code == 401


def test_enroll_heartbeat_and_node_scoped_credential(client):
    headers = {"X-UCF-Admin-Key": "test-admin-key"}
    enrolled = client.put("/v1/nodes/edge-1", json=node_payload(), headers=headers)
    assert enrolled.status_code == 200
    token = enrolled.json()["node_token"]
    assert token

    beat = client.post(
        "/v1/nodes/edge-1/heartbeat",
        json={"cpu_millicores": 6000, "capabilities": ["cpu"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert beat.status_code == 200
    assert beat.json()["status"] == "active"
    assert beat.json()["lease_seconds"] == 45

    wrong_node = client.post(
        "/v1/nodes/other/heartbeat",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert wrong_node.status_code == 403

    again = client.put("/v1/nodes/edge-1", json=node_payload(), headers=headers)
    assert again.status_code == 200
    assert again.json()["node_token"] is None


def test_stale_node_is_not_scheduled(client):
    headers = {"X-UCF-Admin-Key": "test-admin-key"}
    client.put("/v1/nodes/edge-1", json=node_payload(), headers=headers)

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        record = db.get(NodeRecord, "edge-1")
        record.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db.commit()
    finally:
        db.close()
        db_generator.close()

    job = {
        "workload_id": "job-stale",
        "required_capabilities": ["gpu"],
        "cpu_millicores": 1000,
        "memory_mb": 512,
        "gpu_units": 1,
        "max_latency_ms": 80,
        "minimum_trust_level": 1,
        "allowed_tiers": ["edge"],
    }
    response = client.post("/v1/schedule", json=job, headers=headers)
    assert response.status_code == 409
    nodes = client.get("/v1/nodes?include_stale=true", headers=headers).json()
    assert nodes[0]["status"] == "stale"


def test_schedule_uses_persisted_live_inventory(client):
    headers = {"X-UCF-Admin-Key": "test-admin-key"}
    client.put("/v1/nodes/edge-1", json=node_payload(), headers=headers)
    job = {
        "workload_id": "job-1",
        "required_capabilities": ["gpu"],
        "cpu_millicores": 1000,
        "memory_mb": 512,
        "gpu_units": 1,
        "max_latency_ms": 80,
        "minimum_trust_level": 1,
        "allowed_tiers": ["edge"],
        "preferred_tier": "edge",
    }
    response = client.post("/v1/schedule", json=job, headers=headers)
    assert response.status_code == 200
    assert response.json()["selected_node"]["node_id"] == "edge-1"


def test_invalid_node_token_rejected(client):
    response = client.post(
        "/v1/nodes/edge-1/heartbeat",
        json={},
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401



def test_admin_rotation_invalidates_previous_node_token(client):
    admin = {"X-UCF-Admin-Key": "test-admin-key"}
    enrolled = client.put("/v1/nodes/edge-1", json=node_payload(), headers=admin)
    old_token = enrolled.json()["node_token"]

    rotated = client.post("/v1/nodes/edge-1/rotate-token", headers=admin)
    assert rotated.status_code == 200
    new_token = rotated.json()["node_token"]
    assert new_token != old_token

    old_heartbeat = client.post(
        "/v1/nodes/edge-1/heartbeat",
        json={},
        headers={"Authorization": f"Bearer {old_token}"},
    )
    new_heartbeat = client.post(
        "/v1/nodes/edge-1/heartbeat",
        json={},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert old_heartbeat.status_code == 401
    assert new_heartbeat.status_code == 200


def test_node_identifier_rejects_path_unsafe_characters(client):
    response = client.put(
        "/v1/nodes/bad@id",
        json=node_payload("bad@id"),
        headers={"X-UCF-Admin-Key": "test-admin-key"},
    )
    assert response.status_code == 422

from fastapi.testclient import TestClient
from ucf.main import app, _nodes

client = TestClient(app)


def setup_function():
    _nodes.clear()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_and_schedule():
    node = {
        "node_id": "edge-1", "tier": "edge", "region": "eg-cairo",
        "capabilities": ["cpu", "gpu"], "cpu_millicores": 8000,
        "memory_mb": 16384, "gpu_units": 1, "estimated_latency_ms": 15,
        "estimated_cost_per_minute": 0.02, "trust_level": 2, "labels": {},
    }
    assert client.put("/v1/nodes/edge-1", json=node).status_code == 200
    job = {
        "workload_id": "job-1", "required_capabilities": ["gpu"],
        "cpu_millicores": 1000, "memory_mb": 512, "gpu_units": 1,
        "max_latency_ms": 80, "minimum_trust_level": 1,
        "allowed_tiers": ["edge"], "preferred_tier": "edge",
    }
    response = client.post("/v1/schedule", json=job)
    assert response.status_code == 200
    assert response.json()["selected_node"]["node_id"] == "edge-1"


def test_schedule_conflict_when_no_capacity():
    response = client.post("/v1/schedule", json={"workload_id": "missing"})
    assert response.status_code == 409

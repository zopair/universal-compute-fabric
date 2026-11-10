# Control-plane API v0 (prototype)

Base URL: `http://localhost:8000`

- `GET /health`: process health.
- `PUT /v1/nodes/{node_id}`: register/update node inventory.
- `GET /v1/nodes`: list in-memory nodes.
- `DELETE /v1/nodes/{node_id}`: remove node.
- `POST /v1/schedule`: return a placement proposal.

Example node:
```json
{
  "node_id": "edge-egypt-01",
  "tier": "edge",
  "region": "eg-cairo",
  "capabilities": ["cpu", "gpu"],
  "cpu_millicores": 16000,
  "memory_mb": 32768,
  "gpu_units": 1,
  "estimated_latency_ms": 12,
  "estimated_cost_per_minute": 0.02,
  "trust_level": 2,
  "labels": {"provider": "lab"}
}
```

Example workload:
```json
{
  "workload_id": "image-job-001",
  "required_capabilities": ["gpu"],
  "cpu_millicores": 2000,
  "memory_mb": 2048,
  "gpu_units": 1,
  "max_latency_ms": 80,
  "max_cost_per_minute": 0.10,
  "minimum_trust_level": 1,
  "allowed_tiers": ["edge", "cloud"],
  "preferred_tier": "edge"
}
```

A response is a placement decision only; it does not mean execution started.

## Limitations
Inventory is volatile; there is no authentication, persistence, executor, durable queue or tenant isolation. Restart clears inventory.

# UCF Linux Worker Agent

This minimal agent reports currently available CPU and RAM (not total host capacity) to the UCF control plane and renews the node lease. It does **not** execute user workloads, inspect user files, or collect process-level data.

## 1. Enroll the host

Register the node through the administrative API first:

```bash
curl -X PUT "https://UCF_HOST/v1/nodes/worker-01" \
  -H "X-UCF-Admin-Key: $UCF_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "worker-01",
    "tier": "edge",
    "region": "eg-ism",
    "capabilities": ["cpu", "memory", "network"],
    "cpu_millicores": 4000,
    "memory_mb": 8192,
    "gpu_units": 0,
    "estimated_latency_ms": 25,
    "estimated_cost_per_minute": 0,
    "trust_level": 1,
    "labels": {"os": "linux"}
  }'
```

The first enrollment response contains a one-time `node_token`. Store it as a secret; do not put it in source control or logs.

## 2. Install and run

```bash
python -m pip install .
export UCF_CONTROL_PLANE_URL="https://UCF_HOST"
export UCF_NODE_ID="worker-01"
export UCF_NODE_TOKEN="<one-time-token>"
ucf-worker
```

For local development only, `http://127.0.0.1:8000` is allowed. Remote control-plane URLs must use HTTPS. The default heartbeat interval is 15 seconds; the control-plane default lease is 45 seconds.

Optional settings: `UCF_HEARTBEAT_INTERVAL_SECONDS` (5–300), `UCF_GPU_UNITS` (manually declared total GPU units; omitted by default so the agent never overwrites GPU inventory), and `UCF_LOG_LEVEL`. CPU availability is estimated from sampled system utilization; available RAM comes from the OS memory report. These are short-lived estimates, not reservations or guaranteed capacity.

The administrator must set realistic region, trust, latency and cost metadata at enrollment. This agent reports CPU/RAM capacity only; it does not benchmark workload latency or automatically discover GPU hardware.

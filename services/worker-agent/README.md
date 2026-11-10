# UCF Linux Worker Agent

By default, this minimal agent reports currently available CPU and RAM (not total host capacity) to the UCF control plane and renews the node lease. Workload execution is a separate M2 opt-in feature; the agent does not inspect user files or collect process-level data.

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

The administrator must set realistic region, trust, latency and cost metadata at enrollment. This agent reports available CPU/RAM only; it does not benchmark workload-path latency or automatically discover GPU hardware.


## 3. Optional task execution (M2 POC)

Execution is **disabled by default**. To enable the experimental Docker adapter on a dedicated Linux worker:

```bash
export UCF_EXECUTION_ENABLED=true
export UCF_ALLOWED_IMAGE_DIGESTS="ghcr.io/your-org/approved-worker@sha256:<64-hex-digest>"
```

The exact image digest must already exist locally; the executor uses `--pull=never`. Only images listed in `UCF_ALLOWED_IMAGE_DIGESTS` can run. The initial adapter is CPU-only. Tasks requiring GPU are rejected. The agent polls for one task after each successful heartbeat and reports its bounded output and exit status.

The container is launched with no network, read-only root filesystem, no Linux capabilities, no-new-privileges, a non-root UID, CPU/memory/swap/PID limits, a small temporary filesystem, no host mounts and a bounded timeout. Output retained by the agent is capped at 64 KiB per stream. Docker access is highly privileged on the host: use a dedicated test machine, do not expose the Docker socket to workloads, and do not treat this POC container profile as a hardened hostile multi-tenant boundary. Keep execution disabled on shared or production hosts until a stronger runtime and operational recovery are implemented.

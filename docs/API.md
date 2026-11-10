# API

All administrative endpoints use `X-UCF-Admin-Key`. Worker endpoints use the node-scoped bearer token issued at enrollment.

## Health
- `GET /health`
- `GET /ready`

## Nodes
- `PUT /v1/nodes/{node_id}` — enroll or update node inventory
- `GET /v1/nodes` — list active nodes; `include_stale=true` includes stale/pending nodes
- `DELETE /v1/nodes/{node_id}`
- `POST /v1/nodes/{node_id}/heartbeat` — node bearer token
- `POST /v1/nodes/{node_id}/rotate-token` — admin credential rotation

## Placement
- `POST /v1/schedule` — returns a placement proposal only; it does not enqueue or execute work

## Task lifecycle (M2 foundation)
- `POST /v1/tasks` — admin submits a task; the control plane selects an active node and atomically records a resource reservation. Returns HTTP 202.
- `GET /v1/tasks/{task_id}` — admin reads task state and result.
- `POST /v1/worker/tasks/claim` — authenticated worker claims the oldest pending task assigned to its node.
- `POST /v1/worker/tasks/{task_id}/complete` — authenticated assigned worker reports `succeeded` or `failed`; terminal completion releases its reservation.

Task submission includes:
- `workload`: placement requirements and requested CPU, memory and GPU.
- `image`: OCI image reference pinned to a SHA-256 digest.
- `command`: argument array (never a shell command string).
- `timeout_seconds`: bounded to 1–300 seconds.

Reservations are subtracted from reported live capacity when subsequent placements are evaluated. PostgreSQL row-level locking serializes reservation attempts for the same node. The claim response includes CPU, memory and GPU reservation values required by the executor. Execution is at-least-once around worker crashes or lost completion acknowledgements; workloads must be idempotent until stronger deduplication is implemented. The Linux worker can execute tasks only when explicitly enabled with `UCF_EXECUTION_ENABLED=true` and an exact digest-pinned `UCF_ALLOWED_IMAGE_DIGESTS` allowlist. The initial adapter is CPU-only and requires a local Docker image (`--pull=never`). Docker runs with network disabled, a read-only root filesystem, dropped capabilities, non-root UID, CPU/memory/PID limits, bounded execution time and bounded captured output. The executor is a POC isolation boundary, not a production multi-tenant security guarantee.

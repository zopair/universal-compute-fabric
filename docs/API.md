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

Reservations are subtracted from reported live capacity when subsequent placements are evaluated. PostgreSQL row-level locking serializes reservation attempts for the same node. The worker execution adapter is not yet enabled in this milestone: claim/complete endpoints define the dispatch contract, but task submission alone does not run a container. Do not treat the current API as a production execution service.

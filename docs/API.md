# UCF API

Base URL: `http://localhost:8000`

## Health

- `GET /health`: process liveness.
- `GET /ready`: database readiness.

## Administrative authentication

Administrative endpoints accept `X-UCF-Admin-Key`. Configure `UCF_ADMIN_API_KEY` before exposing the service. In production mode (`UCF_ENV=production`), missing admin credentials cause administrative requests to fail closed.

## Node enrollment

`PUT /v1/nodes/{node_id}` requires the admin key and a `ComputeNode` JSON body. The first enrollment returns a one-time `node_token`. Store it securely on the worker. The database stores only its SHA-256 hash. A newly enrolled or re-enrolled node remains `pending` and is not schedulable until it sends an authenticated heartbeat. Re-enrollment does not silently rotate an existing credential.

## Heartbeat and leases

`POST /v1/nodes/{node_id}/heartbeat` requires `Authorization: Bearer <node_token>`. Optional resource fields refresh the live availability snapshot. `available_cpu_millicores` and `available_memory_mb` are kept separate from total `cpu_millicores` and `memory_mb`; the scheduler uses the live available values when present. A successful heartbeat renews the node lease (default 45 seconds). The Linux worker agent in `services/worker-agent` reports estimated available CPU and RAM.

Nodes whose lease expires are marked stale and excluded from scheduling. Expiry is checked during inventory and scheduling requests; a dedicated background reaper can be added when worker volume requires it.

## Inventory

`GET /v1/nodes` lists active nodes. Administrators can request `?include_stale=true` to inspect stale records.

## Credential rotation

`POST /v1/nodes/{node_id}/rotate-token` requires the admin key and immediately invalidates the previous node token. The new token is returned once; securely deliver it to the worker before rotation or expect that worker to remain offline until reconfigured.

## Scheduling

`POST /v1/schedule` requires the admin key. It returns a placement proposal only; it does not execute a workload.

## Security boundary

This milestone provides a single administrative secret and per-node bearer credentials. It is not yet multi-tenant OIDC/RBAC, device attestation, mTLS, or a production-grade secrets rotation service. Do not expose it directly to the public internet until those controls, TLS termination, rate limits, backup/restore, and threat-model review are complete.

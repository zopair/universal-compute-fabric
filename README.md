# Universal Compute Fabric (UCF)

Hybrid edge–cloud workload orchestration for heterogeneous devices.

> Status: M2 experimental execution foundation. UCF schedules explicit workloads across registered nodes; it is not a universal remote CPU, transparent WAN RAM, or a mechanism for running every mobile app remotely. Linux Docker execution is opt-in, CPU-only, and limited to pre-approved digest-pinned images.

## Principles
- Keep interaction loops, safety-critical control, sensors, security boundaries and offline fallback local.
- Place explicit workloads on device, edge or cloud according to hard constraints, latency, locality, trust and cost.
- Do not pretend WAN memory is local process RAM.
- Measure total-system energy, silicon allocation, latency, bandwidth and cost per active user.

## Layout
- `services/control-plane`: FastAPI control plane, SQLAlchemy persistence, leases and placement.
- `services/worker-agent`: Linux telemetry/heartbeat client with optional, allowlisted Docker task execution (disabled by default).
- `services/control-plane/migrations`: Alembic schema migrations.
- `docs/`: architecture, API, roadmap, ADRs and technology assessment.
- `deploy/`: Docker development lab with PostgreSQL.
- `tests/`: scheduler and API tests.
- `.github/workflows/`: CI.

## Run the development lab
1. Copy `.env.example` to `.env`.
2. Set unique values for `POSTGRES_PASSWORD` and `UCF_ADMIN_API_KEY`.
3. Start the services:

```bash
docker compose --env-file .env -f deploy/docker-compose.yml up --build
```

API: http://localhost:8000 · OpenAPI: http://localhost:8000/docs · Liveness: http://localhost:8000/health · Readiness: http://localhost:8000/ready

## Local development
```bash
python -m pip install -e "services/control-plane[dev]" -e services/worker-agent
DATABASE_URL=sqlite:///./ucf.db alembic upgrade head
pytest -q
ruff check services tests
```

Administrative endpoints use `X-UCF-Admin-Key`. First node enrollment returns a one-time node bearer token; store it securely. Workers renew their lease through `POST /v1/nodes/{node_id}/heartbeat`. Scheduling excludes expired leases. `POST /v1/tasks` creates a persisted task and reserves node capacity; authenticated workers claim and complete tasks through the worker API. The optional Docker executor requires `UCF_EXECUTION_ENABLED=true` plus an exact `UCF_ALLOWED_IMAGE_DIGESTS` allowlist and locally preloaded images. See [Linux worker agent](services/worker-agent/README.md) for configuration.

See [architecture](docs/ARCHITECTURE.md), [API](docs/API.md), [roadmap](docs/ROADMAP.md), [open-source technology assessment](docs/OPEN_SOURCE_ASSESSMENT.md), [contributing](CONTRIBUTING.md).

## Security status
The POC includes persistent inventory, a single admin secret, per-node bearer credentials, lease expiry, audit events, task reservations and an optional constrained Docker executor. Execution is disabled by default. The Docker daemon is privileged and the container profile is not a hardened multi-tenant boundary. OIDC/RBAC, tenant isolation, device attestation, mTLS, rate limiting, signed workloads, Firecracker isolation, production threat modeling and recovery remain incomplete. Do not expose the development lab directly to the public internet or submit sensitive workloads.

Apache-2.0. See [LICENSE](LICENSE).

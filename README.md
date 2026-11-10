# Universal Compute Fabric (UCF)

Hybrid edge–cloud workload orchestration for heterogeneous devices.

> Status: M1 control-plane implementation. UCF proposes placement for explicit workloads; it is not a universal remote CPU, transparent WAN RAM, or a mechanism for running every mobile app remotely. Workload execution is not enabled yet.

## Principles
- Keep interaction loops, safety-critical control, sensors, security boundaries and offline fallback local.
- Place explicit workloads on device, edge or cloud according to hard constraints, latency, locality, trust and cost.
- Do not pretend WAN memory is local process RAM.
- Measure total-system energy, silicon allocation, latency, bandwidth and cost per active user.

## Layout
- `services/control-plane`: FastAPI control plane, SQLAlchemy persistence, leases and placement.
- `services/worker-agent`: lightweight Linux host telemetry and heartbeat client.
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
python -m pip install -e "services/control-plane[dev]"
DATABASE_URL=sqlite:///./ucf.db alembic upgrade head
pytest -q
ruff check services tests
```

Administrative endpoints use `X-UCF-Admin-Key`. First node enrollment returns a one-time node bearer token; store it securely. Workers renew their lease through `POST /v1/nodes/{node_id}/heartbeat`. Scheduling excludes expired leases. See [Linux worker agent](services/worker-agent/README.md) for host enrollment and telemetry.

See [architecture](docs/ARCHITECTURE.md), [API](docs/API.md), [roadmap](docs/ROADMAP.md), [open-source technology assessment](docs/OPEN_SOURCE_ASSESSMENT.md), [contributing](CONTRIBUTING.md).

## Security status
M1 includes persistent inventory, a single admin secret, per-node bearer credentials, lease expiry and audit events. It does **not** yet include OIDC/RBAC, tenant isolation, device attestation, mTLS, rate limiting, secret rotation workflow, workload execution isolation, or a production threat-model review. Do not expose the development lab directly to the public internet or submit sensitive workloads.

Apache-2.0. See [LICENSE](LICENSE).

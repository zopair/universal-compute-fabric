# Universal Compute Fabric (UCF)

Hybrid edge–cloud workload orchestration for heterogeneous devices.

> Status: foundation prototype. UCF is not a universal remote CPU, transparent WAN RAM, or a mechanism for running every mobile app remotely. The first milestone is a measurable control plane that proposes workload placement.

## Principles
- Keep interaction loops, safety-critical control, sensors, security boundaries and offline fallback local.
- Place explicit workloads on device, edge or cloud according to hard constraints, latency, locality, trust and cost.
- Do not pretend WAN memory is local process RAM.
- Measure total-system energy, silicon allocation, latency, bandwidth and cost per active user.

## Layout
- `services/control-plane`: FastAPI API and deterministic placement engine.
- `docs/`: architecture, API, roadmap and ADRs.
- `deploy/`: Docker development lab.
- `tests/`: unit and API tests.
- `.github/workflows/`: CI.

## Run
```bash
docker compose -f deploy/docker-compose.yml up --build
```
API: http://localhost:8000 · OpenAPI: http://localhost:8000/docs · Health: http://localhost:8000/health

Local tests:
```bash
python -m pip install -e "services/control-plane[dev]"
pytest
```

See [architecture](docs/ARCHITECTURE.md), [API](docs/API.md), [roadmap](docs/ROADMAP.md), [contributing](CONTRIBUTING.md).

## Security warning
Development-only: no authentication, tenant isolation, persistence, durable queue or workload executor. Do not expose publicly or submit sensitive workloads.

Apache-2.0. See [LICENSE](LICENSE).

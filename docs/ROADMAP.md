# Roadmap

## M0 — Foundation
- [x] Repository and architecture baseline
- [x] Typed node/workload contracts
- [x] Deterministic placement engine
- [x] HTTP API and tests
- [x] Docker lab and CI workflow
- [ ] Verify GitHub Actions run

## M1 — Reliable control plane
- [ ] Follow the open-source adoption plan in [OPEN_SOURCE_ASSESSMENT.md](OPEN_SOURCE_ASSESSMENT.md)
- [ ] PostgreSQL persistence and migrations
- [ ] Heartbeats, leases and stale-node eviction
- [ ] OIDC, RBAC, tenant quotas and audit
- [ ] OpenTelemetry metrics, traces and logs

## M2 — Execution adapters
- [ ] Container executor (containerd/Kubernetes)
- [ ] Firecracker/KVM microVM executor
- [ ] Wasmtime executor for portable modules
- [ ] Signed workload manifests and policy
- [ ] Idempotent lifecycle, cancellation and retries

## M3 — Device clients and sessions
- [ ] Android agent POC
- [ ] Browser client for interactive workloads
- [ ] Device capability and power telemetry
- [ ] Explicit session persistence and handoff
- [ ] Offline/local fallback

## M4 — Federation
- [ ] Multi-region inventory and routing
- [ ] Network-aware placement
- [ ] Data residency and trust zones
- [ ] GPU/NPU provider adapters
- [ ] Admission control and capacity forecasting

## M5 — Evidence-led optimization
- [ ] Benchmark device vs edge vs cloud workloads
- [ ] Measure P50/P95 latency, joules, bandwidth, server energy and cost/user
- [ ] Compare total-system energy and silicon allocation
- [ ] Publish reproducible methodology

No production claim until authentication, isolation, persistence, observability, load testing, threat modeling and recovery are demonstrated.

# UCF Architecture

## Goal and non-goals
UCF is a control plane for selecting where explicit workloads run across device, edge and cloud resources. It does not combine geographically distributed CPUs into one coherent CPU or make internet memory behave like local RAM.

## Layers
1. Device adapters: Android, iOS, Windows, Linux, TV, automotive and IoT.
2. Device agent: enrollment, telemetry, connectivity, cache and local fallback.
3. Identity/session control plane: identity, authorization, device identity, lifecycle and handoff.
4. Workload API and scheduler: requirements, constraints, quotas and admission.
5. Runtimes: containers, microVMs, task workers and portable WASM modules.
6. Resource fabric: CPU, GPU, NPU, memory, storage and network inventory.
7. Infrastructure: edge sites, private clusters and cloud regions.

## Resource inventory and placement
The persistent registry stores total node capacity separately from live available CPU and RAM. Worker heartbeats refresh availability snapshots; stale leases are excluded. These values are estimates, not reservations. Before concurrent workload execution is enabled, the executor must add atomic resource reservations and release/reconciliation on completion or failure.

A workload declares required capabilities, CPU/memory/GPU, latency budget, locality, trust, energy/cost preference, runtime constraints and fallback behavior. The scheduler filters ineligible nodes before scoring candidates. Hard constraints are never traded for a better score. The initial score is a transparent heuristic, not ML.

## Execution tiers
- Device: interaction loops, sensors, camera pipeline, safety and offline behavior.
- Edge: latency-sensitive but offloadable work near the user.
- Cloud: batch, elastic, long-running or accelerator-heavy work where latency permits.

## Control plane and data plane
Control plane: HTTPS/gRPC for identity, inventory, scheduling and lifecycle. Data plane: workload-specific transport; WebRTC may suit interactive audio/video, while QUIC may suit multiplexed streams. Benchmark before selecting.

## Isolation
Containers for compatible workloads; microVMs (Firecracker/KVM) for stronger isolation; WebAssembly for portable constrained modules. The current scheduler does not launch workloads.

## Session continuity
Persist application state explicitly and rehydrate it on compatible targets. Handoff is not arbitrary process migration between unlike operating systems.

## Reliability
Node heartbeats and lease expiry; bounded retries and idempotency keys; quotas; circuit breakers; local fallback on connectivity failure.

## Production security gates
OIDC/OAuth2, device attestation where available, mTLS, tenant authorization, secrets management, signed workload artifacts, sandboxing, audit logs, rate limits, data residency and threat modeling.

See [ADRs](adr/README.md). Performance and energy claims require repeatable measurements.

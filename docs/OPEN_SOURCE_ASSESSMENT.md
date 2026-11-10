# Open-Source Technology Assessment and Adoption Plan

**Assessment date:** 2026-11-10  
**Scope:** technologies that can materially advance Universal Compute Fabric (UCF).  
**Decision rule:** reuse mature, licensed components for commodity infrastructure; build UCF-specific orchestration and policy where the product differentiates.

## 1. Executive decision

UCF should be a vendor-neutral control plane over existing runtimes and infrastructure, not a new hypervisor, container engine, AI model server, or remote-desktop protocol.

Recommended baseline:

- **Control plane:** retain the existing FastAPI service initially; add PostgreSQL persistence, OIDC-compatible identity, policy enforcement, and OpenTelemetry.
- **Cluster / edge orchestration:** Kubernetes as an optional deployment substrate, not a mandatory dependency for the first single-host POC. Evaluate K3s for small edge sites.
- **Durable workflows and service plumbing:** Dapr selectively for durable workflow, service invocation, state, pub/sub, and workload identity. Do not make every Dapr capability a hard dependency.
- **Execution isolation:** containerd for OCI containers; Firecracker/KVM for stronger microVM isolation; gVisor as an alternative sandbox runtime; Wasmtime for portable WASM modules.
- **Interactive remote sessions:** Selkies for Linux desktop streaming; benchmark WebRTC and its supported transports under actual network conditions. Keep session orchestration and identity in UCF.
- **Distributed AI / accelerator workloads:** integrate specialized backends such as Ray, vLLM, and Meta Monarch behind adapters. These are workload-specific execution systems, not the general UCF scheduler.
- **Agents for engineering and operations:** use agent frameworks as optional development/operations assistants with explicit permissions, isolated workspaces, logs, and human approval. Agents must not be trusted as the security boundary or scheduler source of truth.

The differentiating UCF code should remain: normalized device/resource model, capability and trust registry, placement policy, network/energy/cost-aware scheduling, cross-runtime adapter contracts, explicit session handoff, and reproducible measurement.

## 2. Candidate assessment

| Source / project | Relevant capability | UCF decision | Important limitation |
|---|---|---|---|
| Google **gVisor** — https://github.com/google/gvisor | Userspace application kernel and OCI sandbox runtime | Evaluate as a sandbox option for untrusted container workloads | Linux host/runtime compatibility and workload syscall compatibility must be tested |
| Google **ADK** — https://github.com/google/adk-python | Open-source multi-agent framework; Apache-2.0 | Optional agent orchestration for research/devops workflows | Not a compute scheduler or workload isolation system |
| OpenAI **Codex CLI / SDK / app-server** — https://github.com/openai/codex | Inspectable coding-agent harness and SDK | Use as an optional engineering agent; integrate only through controlled tools | Codex cloud is not the same thing as the open-source CLI/harness; model access may have separate costs and terms |
| Anthropic **SDKs / MCP ecosystem** — https://github.com/anthropics | Model API SDKs and tool interoperability | Use MCP as an integration protocol where it simplifies agent/tool access | SDKs do not make Claude models open source; API usage is governed by provider terms |
| DeepSeek **DeepInfer** — https://github.com/deepseek-ai/DeepInfer | Specialized inference runtime for supported DeepSeek models | Optional AI inference adapter after hardware/model benchmarks | Model-specific; not a general-purpose compute fabric |
| DeepSeek **deepseek-harness** — https://github.com/deepseek-ai/deepseek-harness | Agent harness and MCP tool integration | Evaluate as an optional agent implementation | Agent runtime only; verify license, maturity, and model compatibility before adoption |
| Microsoft / CNCF **Dapr** — https://github.com/dapr/dapr | Portable cloud/edge runtime, durable workflows, service invocation, state, pub/sub, mTLS | Adopt selectively for reliability plumbing after a focused POC | Sidecar and operational footprint; avoid duplicating UCF's placement logic |
| Microsoft / CNCF **KEDA** — https://github.com/kedacore/keda | Event-driven Kubernetes autoscaling, including scale-to-zero | Optional scale-out adapter for Kubernetes deployments | Kubernetes-centric; does not place tasks across arbitrary personal devices |
| Microsoft **Wasm Micro Runtime** — https://github.com/bytecodealliance/wasm-micro-runtime | Small WebAssembly runtime for edge/IoT | Benchmark against Wasmtime for constrained device/edge targets | WASM workload portability requires a defined ABI and capability model |
| Meta **Monarch** — https://github.com/meta-pytorch/monarch | Distributed actors, supervision, tensor and RDMA support for PyTorch | Optional specialized backend for distributed AI/tensor jobs | Not appropriate for ordinary app workloads or wide-area shared memory; GPU/RDMA features have platform prerequisites |
| Apple **Container / Containerization** — https://github.com/apple/container and https://github.com/apple/containerization | Linux containers in lightweight VMs on Apple silicon | Study for a future macOS/Apple Silicon worker adapter | Requires supported macOS and Apple Silicon; not a cross-platform UCF runtime |
| xAI | Public repositories located in this scan did not reveal a clearly relevant, maintained general-purpose compute runtime | No core dependency selected | xAI model/API access is distinct from open-source infrastructure |
| Lovable | No official Lovable-owned general-purpose compute runtime identified in this scan | Do not depend on third-party “Lovable clone” repos | Unofficial clones and extracted prompts are not evidence of source access or permission to reproduce proprietary internals |
| Selkies — https://github.com/selkies-project/selkies | Browser-based Linux desktop / GPU streaming | Preferred remote-session POC candidate | Streaming only; UCF still owns scheduling, auth, lifecycle and state |
| Firecracker — https://github.com/firecracker-microvm/firecracker | KVM-based lightweight microVM isolation; Apache-2.0 | Preferred stronger-isolation execution candidate on compatible Linux hosts | Requires KVM and carefully configured host; not available on every device/host |
| Kubernetes — https://github.com/kubernetes/kubernetes | Container orchestration and placement substrate | Optional multi-node deployment backend | Kubernetes scheduler is not the UCF cross-domain policy engine |
| Wasmtime — https://github.com/bytecodealliance/wasmtime | WebAssembly runtime | Preferred initial WASM runtime candidate, subject to target testing | WASM modules need explicit host APIs/capabilities |
| Ray — https://github.com/ray-project/ray | Distributed Python tasks and actors | Adapter for Python/AI workloads where justified | Not a universal runtime and can be heavy for the first POC |
| vLLM — https://github.com/vllm-project/vllm | High-throughput model inference serving | AI inference adapter for supported hardware/models | GPU/vendor support and model licensing must be checked per deployment |
| OpenTelemetry — https://github.com/open-telemetry | Vendor-neutral metrics, traces and logs | Adopt for control-plane and worker observability | Telemetry needs privacy controls and retention policy |
| PostgreSQL — https://github.com/postgres/postgres | Durable relational state | Adopt for nodes, leases, sessions, tenants and audit metadata | Backups, migrations and HA are operational responsibilities |

## 3. Provider and project boundaries

A vendor's public GitHub organization is not equivalent to its full product source code. UCF will distinguish:

1. **Open source:** source code and a license are available; comply with the license and notices.
2. **Source-available / model weights:** usage, redistribution, and commercial rights may be restricted by a separate license.
3. **Hosted API:** callable service, but not a self-hostable runtime; pricing, data handling, rate limits, and terms apply.
4. **Closed product:** no assumption of source access. Use documented APIs only, or build an independent implementation from public standards and observed permitted behavior.

For each dependency, before production adoption, record the exact repository URL, pinned release/commit, SPDX license, transitive notices, security policy, maintenance signals, supported platforms, and an exit/replacement path. Re-check these at the time of integration; this assessment is a shortlist, not a legal opinion or a permanent maintenance guarantee.

## 4. What UCF should build itself

Build the product-specific layer rather than recreating commodity infrastructure:

- **Resource contract:** normalized CPU/GPU/NPU/memory/storage/network/accelerator capabilities, architecture, locality, trust zone, availability and measurement confidence.
- **Worker agent:** authenticated enrollment, heartbeat/lease, telemetry, capability discovery, policy-limited task lifecycle and local fallback.
- **Placement engine:** hard eligibility filters followed by explainable scoring for latency, cost, energy, locality, trust and queue pressure.
- **Adapter interface:** common lifecycle contract for containerd/Kubernetes, Firecracker, Wasmtime, Ray and remote-session runtimes.
- **Network-aware placement:** active probes and per-path estimates; never assume a single global latency value.
- **Session state and handoff:** explicit checkpoint/state transfer between compatible runtimes, not arbitrary process migration or WAN RAM.
- **Energy and silicon accounting:** measure client energy, worker energy, network energy where estimable, and amortized infrastructure allocation. Report uncertainty.
- **Policy and audit layer:** tenant quotas, consent, data residency, workload signing, revocation and tamper-evident events.

Do **not** build a new hypervisor, general container engine, database, cryptographic protocol, video codec, or LLM inference engine unless a measured requirement cannot be met by existing projects.

## 5. Agent strategy

Agents can accelerate UCF engineering, repository research, test generation, issue triage and controlled operations. They are not a substitute for deterministic code.

Recommended role separation:

- **Research agent:** searches official documentation and repositories; outputs evidence, versions and license notes.
- **Architecture agent:** proposes changes but cannot merge or deploy.
- **Implementation agent:** works in a scoped branch/worktree with tests and no production secrets.
- **Review/security agent:** checks diffs, dependency licenses, threat model and test gaps independently.
- **Release operator:** runs approved CI/deployment steps only after human approval.

Use MCP or provider SDKs as connectors, but expose narrow allow-listed tools. Every agent action should have an identity, run ID, inputs/outputs, timeouts, resource quotas and audit record. Never allow an agent to run arbitrary code on a shared worker without sandboxing.

## 6. Proposed integration sequence

### M1. Reliable control plane (next)
1. PostgreSQL schema and migrations for nodes, node leases, workloads, sessions and audit events.
2. Heartbeat endpoint with lease expiry and stale-node exclusion.
3. Worker enrollment credentials and rotation; OIDC for human/operator identity.
4. OpenTelemetry instrumentation and a minimal operational dashboard.
5. Contract tests and CI for API, persistence, lease expiry and scheduler behavior.

### M2. First real execution
1. Implement one Linux container adapter using containerd or a clearly scoped Docker-compatible development adapter.
2. Add a signed workload manifest and strict resource/time/network limits.
3. Run untrusted test workloads under gVisor or Firecracker where supported.
4. Add a Wasmtime adapter for a tiny portable task format.
5. Keep execution disabled by default until security tests pass.

### M3. Device and interactive session POC
1. Integrate Selkies for remote Linux desktop sessions.
2. Add a browser client and a minimal Android client/agent for identity, telemetry and session access.
3. Measure LAN, Wi-Fi, 4G/5G and internet latency, frame rate, bandwidth and device energy.
4. Test explicit session reconnect and state restoration.

### M4. Specialized backends and federation
1. Add Ray/vLLM/Monarch adapters only for workloads that need them.
2. Add optional Kubernetes/KEDA backend for multi-node sites.
3. Evaluate Dapr for durable workflow and cross-service reliability.
4. Add multi-region routing, data residency and network-aware scheduling.

## 7. Acceptance gates

A component is not “integrated” merely because it appears in documentation. Each integration needs:

- Pinned version and recorded license.
- Automated build and compatibility tests.
- Functional contract tests through the UCF adapter.
- Failure, timeout, cancellation and restart tests.
- Isolation and authorization tests appropriate to the workload.
- Benchmarks against a baseline on named hardware and network conditions.
- Documented cost, operational burden and removal path.

No claim of reduced total silicon or energy until repeated end-to-end measurements include client, network and server-side costs.

## 8. Research references

- Google gVisor: https://github.com/google/gvisor
- Google ADK: https://github.com/google/adk-python
- OpenAI Codex: https://github.com/openai/codex
- Anthropic repositories: https://github.com/anthropics
- DeepSeek DeepInfer: https://github.com/deepseek-ai/DeepInfer
- DeepSeek Harness: https://github.com/deepseek-ai/deepseek-harness
- Dapr: https://github.com/dapr/dapr
- KEDA: https://github.com/kedacore/keda
- Wasm Micro Runtime: https://github.com/bytecodealliance/wasm-micro-runtime
- Meta Monarch: https://github.com/meta-pytorch/monarch
- Apple Container: https://github.com/apple/container
- Apple Containerization: https://github.com/apple/containerization
- Selkies: https://github.com/selkies-project/selkies
- Firecracker: https://github.com/firecracker-microvm/firecracker
- Wasmtime: https://github.com/bytecodealliance/wasmtime
- Ray: https://github.com/ray-project/ray
- vLLM: https://github.com/vllm-project/vllm
- OpenTelemetry: https://github.com/open-telemetry
- PostgreSQL: https://github.com/postgres/postgres


## 9. M1 implementation outcome and evidence

The first practical integration set is deliberately smaller than the candidate list:

- **PostgreSQL + SQLAlchemy 2 + Alembic:** selected for durable node inventory, lease timestamps, credential hashes and audit events. SQLite is retained for isolated tests and local development, not as the multi-node production datastore. SQLAlchemy's documented session-per-request/task lifecycle informs the API's scoped database dependency.
- **OpenTelemetry Python:** FastAPI tracing instrumentation is wired into the control plane. Export is optional through an OTLP/HTTP endpoint; a collector and dashboard are not bundled, and metrics/log pipelines remain future work. The Python project's current documentation marks traces and metrics stable while logs remain in development.
- **Linux worker agent:** a small independent Python package reports sampled available CPU and OS-reported available RAM over HTTPS, then renews a node lease. It does not execute tasks, auto-discover GPUs, estimate end-user network paths, or reserve resources.
- **Scheduler correction:** total CPU/RAM and currently available CPU/RAM are distinct. The scheduler uses live availability when a heartbeat has supplied it, while retaining total capacity as a fallback for nodes without telemetry. These are snapshots, not reservations; concurrent execution must wait for atomic resource reservation accounting.

### Explicitly deferred

Dapr, Kubernetes/K3s, KEDA, gVisor, Firecracker, Wasmtime, Ray, vLLM, Monarch and Selkies are not installed in the current runtime. They remain candidate adapters or infrastructure options. The first worker agent and control plane do not yet launch workloads. Kubernetes/K3s should be introduced only when multiple execution hosts and cluster lifecycle needs justify it. Firecracker requires compatible Linux/KVM hosts; gVisor has documented syscall and device compatibility gaps, so each untrusted workload class needs a compatibility test before it can be the default sandbox.

### Current completion boundary

M1 now has persistent node inventory, schema migration, per-node credentials, admin-key protection, credential rotation, heartbeat/lease expiry, stale-node exclusion, audit events, basic trace instrumentation and a Linux telemetry agent. OIDC/RBAC, tenant isolation/quotas, mTLS, metrics/log dashboards, periodic lease reaping, load testing and threat-model review remain open. M2 workload execution is not implemented.

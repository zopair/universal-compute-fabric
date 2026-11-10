# Security by Development Stage

UCF is currently an experimental proof of concept. Security work must protect the current lab and avoid choices that would force an architectural rewrite, but must not introduce production-scale controls before they are useful.

## Current POC baseline

Keep the active development path lightweight:

- Keep node credentials and the administrative API key out of source control; store only node-token hashes in the database.
- Require HTTPS for worker-to-control-plane traffic outside loopback development environments.
- Keep the existing node enrollment, heartbeat, lease-expiry and token-rotation checks.
- Do not execute arbitrary workload code directly on the host. Until an executor with an appropriate sandbox exists, placement remains a proposal only.
- Use isolated test data and non-production credentials in the experimental environment.
- Add focused tests for security-sensitive behavior when changing the related code.

These controls are part of keeping the experiment safe and reproducible; they are not a claim that the platform is production-secure.

## Defer until the relevant capability is introduced

Do not block the POC on enterprise-scale identity, policy or operations infrastructure. Add these when real multi-user execution, external node operators, or production deployment makes them necessary:

- OIDC/SSO, fine-grained RBAC and tenant quotas.
- Advanced secrets management and key rotation automation.
- Full security event pipeline, dashboards, alerting and formal incident procedures.
- Formal threat modeling, penetration testing and compliance controls.
- Advanced workload policy and signed manifests beyond the minimum required by the first executor.

## Stage gates

1. **POC connectivity and placement:** protect credentials, validate node identity, use safe transport, and keep placement separate from execution.
2. **First workload executor:** introduce a practical sandbox and enforce basic CPU, memory, time and filesystem/network limits before running untrusted workloads.
3. **Multi-user or third-party nodes:** add tenant isolation, stronger identity and authorization, quotas, and operational audit controls.
4. **Production deployment:** complete threat modeling, security testing, monitoring, recovery and operational hardening.

## Working rule

Choose the least complex control that adequately addresses a real risk at the current stage. Do not defer a safety measure that prevents immediate credential exposure, host compromise or cross-workload interference; do defer controls whose operational cost is not justified by the current POC.

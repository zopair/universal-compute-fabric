# UCF — Preview Readiness

## What to preview
UCF is an experimental hybrid edge/cloud workload control plane. The preview should demonstrate node registration, heartbeat/lease handling, task placement, and worker execution only in a disposable local lab.

## Fast local preview
Requirements: Docker Engine + Docker Compose.

1. Copy `.env.example` to `.env`.
2. Set unique, local-only values for `POSTGRES_PASSWORD` and `UCF_ADMIN_API_KEY`.
3. Start the lab:

```bash
docker compose --env-file .env -f deploy/docker-compose.yml up --build
```

4. Inspect:
   - API: http://127.0.0.1:8000
   - OpenAPI: http://127.0.0.1:8000/docs
   - Liveness: http://127.0.0.1:8000/health
   - Readiness: http://127.0.0.1:8000/ready

Stop with `docker compose -f deploy/docker-compose.yml down`. Add `-v` only when intentionally deleting the local database volume.

## Suggested 5-minute walkthrough
1. Show the control-plane health and readiness endpoints.
2. Enroll a disposable worker and explain its one-time node token.
3. Show heartbeat renewal and lease expiry behavior.
4. Submit a harmless task and show reservation, claim, and completion.
5. Explain placement constraints and why WAN memory is not treated as local RAM.

## Preview acceptance
- [ ] PostgreSQL and control-plane become healthy.
- [ ] Admin endpoints reject missing/invalid credentials.
- [ ] A worker can enroll and renew its lease.
- [ ] Expired leases are excluded from placement.
- [ ] A task is reserved, claimed, and completed exactly once.
- [ ] CI and PostgreSQL concurrency tests are green.

## Safety boundary
Keep the preview on localhost. Docker execution is opt-in and requires exact digest-pinned image allowlisting. The Docker daemon is privileged; the current container profile is not a hardened multi-tenant boundary. OIDC/RBAC, tenant isolation, device attestation, mTLS, signed workloads, stronger isolation, and production recovery remain incomplete. Do not use sensitive workloads or expose this lab to the public internet.

## Reviewer evidence
Provide CI links, sanitized API request/response examples, the image digest if execution is enabled, and the exact compose configuration used. Do not publish tokens or the local `.env` file.

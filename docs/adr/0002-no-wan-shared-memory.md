# ADR 0002: No transparent WAN-backed process memory

- Status: Accepted
- Date: 2026-11-10

## Context
Network latency and failure behavior are incompatible with treating remote memory as ordinary local RAM for general CPU load/store operations.

## Decision
Do not expose WAN memory as transparent process RAM. Use explicit task APIs, remote services, caches and durable state. Memory pooling may be evaluated inside compatible data-center fabrics (for example, CXL), not assumed to extend to phones over the internet.

## Consequences
Applications must be partitioned into offloadable tasks/services. Session state is serialized and restored explicitly.

# ADR 0001: Hybrid edge–cloud placement

- Status: Accepted
- Date: 2026-11-10

## Context
Reduce client compute requirements without making device usability depend on remote connectivity.

## Decision
Adopt hybrid placement across device, edge and cloud. Keep real-time, safety-critical, privacy-constrained and connectivity-critical functions local. Offload only explicit workloads whose requirements and policy permit it.

## Alternatives
Cloud-only was rejected due to latency, availability, privacy and safety. Fully local was rejected as the sole model because it cannot elastically use shared accelerators and remote capacity.

## Consequences
Workloads require explicit contracts, locality and fallback. Savings must be evaluated across client and infrastructure energy, silicon and cost.

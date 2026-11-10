from __future__ import annotations

from ucf.models import CandidateScore, ComputeNode, PlacementDecision, WorkloadRequest


def _eligibility_reasons(node: ComputeNode, job: WorkloadRequest) -> list[str]:
    failures: list[str] = []
    if node.tier not in job.allowed_tiers:
        failures.append("tier_not_allowed")
    if not job.required_capabilities.issubset(node.capabilities):
        failures.append("missing_capability")
    if node.cpu_millicores < job.cpu_millicores:
        failures.append("insufficient_cpu")
    if node.memory_mb < job.memory_mb:
        failures.append("insufficient_memory")
    if node.gpu_units < job.gpu_units:
        failures.append("insufficient_gpu")
    if node.estimated_latency_ms > job.max_latency_ms:
        failures.append("latency_budget_exceeded")
    if node.trust_level < job.minimum_trust_level:
        failures.append("trust_level_too_low")
    if job.max_cost_per_minute is not None and node.estimated_cost_per_minute > job.max_cost_per_minute:
        failures.append("cost_budget_exceeded")
    return failures


def schedule(job: WorkloadRequest, nodes: list[ComputeNode]) -> PlacementDecision:
    """Return a deterministic placement proposal; never starts a workload."""
    ranked: list[CandidateScore] = []
    eligible: list[tuple[float, ComputeNode]] = []

    for node in nodes:
        if _eligibility_reasons(node, job):
            continue
        latency_score = max(0.0, 1.0 - node.estimated_latency_ms / job.max_latency_ms)
        cost_ceiling = job.max_cost_per_minute or max(node.estimated_cost_per_minute, 1.0)
        cost_score = max(0.0, 1.0 - node.estimated_cost_per_minute / max(cost_ceiling, 0.000001))
        tier_score = 1.0 if job.preferred_tier == node.tier else 0.0
        score = round(0.55 * latency_score + 0.30 * cost_score + 0.15 * tier_score, 6)
        reasons = [f"latency={node.estimated_latency_ms:g}ms",
                   f"cost_per_minute={node.estimated_cost_per_minute:g}"]
        if job.preferred_tier == node.tier:
            reasons.append("preferred_tier")
        ranked.append(CandidateScore(node_id=node.node_id, score=score, reasons=reasons))
        eligible.append((score, node))

    ranked.sort(key=lambda item: (-item.score, item.node_id))
    if not eligible:
        return PlacementDecision(
            workload_id=job.workload_id, status="no_eligible_node",
            explanation="No node satisfies all hard workload constraints.",
        )

    eligible.sort(key=lambda item: (-item[0], item[1].node_id))
    return PlacementDecision(
        workload_id=job.workload_id, status="placement_proposed",
        selected_node=eligible[0][1], candidates=ranked,
        explanation="A placement proposal was selected; execution has not been started.",
    )

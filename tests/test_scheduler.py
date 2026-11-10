from ucf.models import ComputeNode, Tier, WorkloadRequest
from ucf.scheduler import schedule


def make_node(node_id="edge-1", **overrides):
    data = dict(
        node_id=node_id, tier=Tier.EDGE, region="eg-cairo",
        capabilities={"cpu", "gpu"}, cpu_millicores=8000, memory_mb=16384,
        gpu_units=1, estimated_latency_ms=15, estimated_cost_per_minute=0.02,
        trust_level=2,
    )
    data.update(overrides)
    return ComputeNode(**data)


def make_job(**overrides):
    data = dict(
        workload_id="job-1", required_capabilities={"gpu"},
        cpu_millicores=2000, memory_mb=2048, gpu_units=1,
        max_latency_ms=80, minimum_trust_level=1,
        allowed_tiers={Tier.EDGE, Tier.CLOUD}, preferred_tier=Tier.EDGE,
    )
    data.update(overrides)
    return WorkloadRequest(**data)


def test_selects_eligible_node():
    decision = schedule(make_job(), [make_node()])
    assert decision.status == "placement_proposed"
    assert decision.selected_node.node_id == "edge-1"


def test_hard_constraints_cannot_be_traded_for_score():
    weak = make_node("weak", gpu_units=0)
    capable = make_node("capable", estimated_latency_ms=30)
    decision = schedule(make_job(), [weak, capable])
    assert decision.selected_node.node_id == "capable"


def test_no_eligible_node():
    decision = schedule(make_job(max_latency_ms=5), [make_node()])
    assert decision.status == "no_eligible_node"
    assert decision.selected_node is None


def test_tie_break_is_deterministic():
    decision = schedule(make_job(), [make_node("z"), make_node("a")])
    assert decision.selected_node.node_id == "a"



def test_live_available_capacity_overrides_total_host_capacity():
    overloaded = make_node(
        "busy",
        cpu_millicores=16000,
        memory_mb=32768,
        available_cpu_millicores=500,
        available_memory_mb=256,
    )
    healthy = make_node(
        "ready",
        cpu_millicores=16000,
        memory_mb=32768,
        available_cpu_millicores=8000,
        available_memory_mb=8192,
    )
    decision = schedule(make_job(), [overloaded, healthy])
    assert decision.status == "placement_proposed"
    assert decision.selected_node.node_id == "ready"

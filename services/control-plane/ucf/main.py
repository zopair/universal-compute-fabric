from fastapi import FastAPI, HTTPException
from ucf.models import ComputeNode, WorkloadRequest
from ucf.scheduler import schedule

app = FastAPI(
    title="Universal Compute Fabric Control Plane",
    version="0.1.0",
    description="Development prototype: inventory and workload placement proposals only.",
)

# Volatile prototype inventory. Replace with persistent storage and leases in M1.
_nodes: dict[str, ComputeNode] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ucf-control-plane", "stage": "prototype"}


@app.put("/v1/nodes/{node_id}", response_model=ComputeNode)
def upsert_node(node_id: str, node: ComputeNode) -> ComputeNode:
    if node_id != node.node_id:
        raise HTTPException(status_code=400, detail="Path node_id must match body node_id")
    _nodes[node_id] = node
    return node


@app.get("/v1/nodes", response_model=list[ComputeNode])
def list_nodes() -> list[ComputeNode]:
    return sorted(_nodes.values(), key=lambda item: item.node_id)


@app.delete("/v1/nodes/{node_id}")
def delete_node(node_id: str) -> dict[str, str]:
    if node_id not in _nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    del _nodes[node_id]
    return {"status": "deleted", "node_id": node_id}


@app.post("/v1/schedule")
def propose_placement(job: WorkloadRequest):
    decision = schedule(job, list(_nodes.values()))
    if decision.status == "no_eligible_node":
        raise HTTPException(status_code=409, detail=decision.model_dump(mode="json"))
    return decision

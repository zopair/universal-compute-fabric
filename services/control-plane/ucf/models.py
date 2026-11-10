from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class Tier(StrEnum):
    DEVICE = "device"
    EDGE = "edge"
    CLOUD = "cloud"


class ComputeNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str = Field(min_length=1, max_length=128)
    tier: Tier
    region: str = Field(min_length=1, max_length=64)
    capabilities: set[str] = Field(default_factory=set)
    cpu_millicores: int = Field(gt=0)
    memory_mb: int = Field(gt=0)
    gpu_units: int = Field(default=0, ge=0)
    estimated_latency_ms: float = Field(ge=0)
    estimated_cost_per_minute: float = Field(ge=0)
    trust_level: int = Field(default=0, ge=0, le=5)
    labels: dict[str, str] = Field(default_factory=dict)


class WorkloadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workload_id: str = Field(min_length=1, max_length=128)
    required_capabilities: set[str] = Field(default_factory=set)
    cpu_millicores: int = Field(default=1000, gt=0)
    memory_mb: int = Field(default=512, gt=0)
    gpu_units: int = Field(default=0, ge=0)
    max_latency_ms: float = Field(default=100, gt=0)
    max_cost_per_minute: float | None = Field(default=None, ge=0)
    minimum_trust_level: int = Field(default=0, ge=0, le=5)
    allowed_tiers: set[Tier] = Field(default_factory=lambda: set(Tier))
    preferred_tier: Tier | None = None


class CandidateScore(BaseModel):
    node_id: str
    score: float
    reasons: list[str]


class PlacementDecision(BaseModel):
    workload_id: str
    status: str
    selected_node: ComputeNode | None = None
    candidates: list[CandidateScore] = Field(default_factory=list)
    explanation: str

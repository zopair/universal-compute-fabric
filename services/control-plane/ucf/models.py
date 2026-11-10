from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Tier(StrEnum):
    DEVICE = "device"
    EDGE = "edge"
    CLOUD = "cloud"


class ComputeNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    tier: Tier
    region: str = Field(min_length=1, max_length=64)
    capabilities: set[str] = Field(default_factory=set)
    cpu_millicores: int = Field(gt=0)
    memory_mb: int = Field(gt=0)
    available_cpu_millicores: int | None = Field(default=None, ge=0)
    available_memory_mb: int | None = Field(default=None, ge=0)
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


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workload: WorkloadRequest
    image: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._/:@-]{1,254}@sha256:[a-f0-9]{64}$")
    command: list[str] = Field(min_length=1, max_length=64)
    timeout_seconds: int = Field(default=30, ge=1, le=300)

    @model_validator(mode="after")
    def validate_runtime_limits(self):
        if self.workload.cpu_millicores < 100 or self.workload.memory_mb < 64:
            raise ValueError("Docker tasks require at least 100 millicores and 64 MB memory")
        if self.workload.gpu_units:
            raise ValueError("GPU tasks are not supported by the initial CPU-only executor")
        return self

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: list[str]) -> list[str]:
        if any(not item or len(item) > 4096 for item in value):
            raise ValueError("Command arguments must be non-empty and at most 4096 characters")
        if sum(len(item) for item in value) > 16384:
            raise ValueError("Command payload is too large")
        return value


class TaskResponse(BaseModel):
    task_id: str
    status: str
    assigned_node_id: str
    image: str
    command: list[str]
    timeout_seconds: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exit_code: int | None = None
    result: str | None = None
    error: str | None = None


class TaskClaimResponse(BaseModel):
    task: TaskResponse | None


class TaskCompletionRequest(BaseModel):
    status: str = Field(pattern=r"^(succeeded|failed)$")
    exit_code: int = Field(ge=0, le=255)
    result: str | None = Field(default=None, max_length=65536)
    error: str | None = Field(default=None, max_length=8192)


class NodeEnrollmentResponse(BaseModel):
    node: ComputeNode
    node_token: str | None
    lease_seconds: int
    credential_note: str


class HeartbeatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available_cpu_millicores: int | None = Field(default=None, ge=0)
    available_memory_mb: int | None = Field(default=None, ge=0)
    gpu_units: int | None = Field(default=None, ge=0)
    capabilities: set[str] | None = None
    estimated_latency_ms: float | None = Field(default=None, ge=0)


class HeartbeatResponse(BaseModel):
    node_id: str
    status: str
    server_time: datetime
    lease_expires_at: datetime
    lease_seconds: int


class NodeStatusResponse(BaseModel):
    node: ComputeNode
    status: str
    last_seen_at: datetime | None
    lease_expires_at: datetime | None

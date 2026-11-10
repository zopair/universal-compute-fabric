from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ucf.entities import NodeRecord
from ucf.models import TaskCreateRequest, Tier, WorkloadRequest
from ucf.repository import create_task_with_reservation, utcnow


def test_postgres_row_lock_prevents_concurrent_overreservation():
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith(("postgresql://", "postgresql+")):
        pytest.skip("This integration test requires PostgreSQL")

    engine = create_engine(database_url, pool_size=5, max_overflow=0)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    node_id = f"reservation-race-{uuid4().hex}"
    now = utcnow()

    try:
        with sessions() as db:
            db.add(NodeRecord(
                node_id=node_id,
                tier="edge",
                region="ci",
                capabilities=["cpu", "memory"],
                cpu_millicores=2000,
                memory_mb=4096,
                available_cpu_millicores=1000,
                available_memory_mb=2048,
                gpu_units=0,
                estimated_latency_ms=10,
                estimated_cost_per_minute=0,
                trust_level=1,
                labels={},
                status="active",
                last_seen_at=now,
                lease_expires_at=now + timedelta(minutes=5),
                credential_hash=hashlib.sha256(node_id.encode()).hexdigest(),
                created_at=now,
                updated_at=now,
            ))
            db.commit()

        barrier = Barrier(2)

        def submit(index: int) -> bool:
            payload = TaskCreateRequest(
                workload=WorkloadRequest(
                    workload_id=f"{node_id}-task-{index}",
                    required_capabilities={"cpu"},
                    cpu_millicores=700,
                    memory_mb=512,
                    gpu_units=0,
                    max_latency_ms=100,
                    minimum_trust_level=0,
                    allowed_tiers={Tier.EDGE},
                ),
                image="ghcr.io/example/worker@sha256:" + "a" * 64,
                command=["/bin/true"],
                timeout_seconds=10,
            )
            with sessions() as db:
                barrier.wait(timeout=10)
                try:
                    create_task_with_reservation(db, payload, node_id)
                    return True
                except ValueError:
                    db.rollback()
                    return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(submit, (1, 2)))

        assert sorted(outcomes) == [False, True]
    finally:
        engine.dispose()

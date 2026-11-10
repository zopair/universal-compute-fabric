from __future__ import annotations

import os
from uuid import uuid4

import pytest

from ucf_worker.executor import DockerExecutor


def test_docker_executor_runs_digest_pinned_local_image():
    image_ref = os.getenv("UCF_TEST_IMAGE_REF")
    if not image_ref:
        pytest.skip("UCF_TEST_IMAGE_REF is set only by the Docker integration workflow")

    executor = DockerExecutor({image_ref})
    result = executor.execute({
        "task_id": f"docker-smoke-{uuid4().hex}",
        "image": image_ref,
        "command": ["/smoke"],
        "cpu_millicores": 100,
        "memory_mb": 64,
        "timeout_seconds": 10,
    })

    assert result.status == "succeeded"
    assert result.exit_code == 0
    assert result.error is None

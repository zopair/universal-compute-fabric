from ucf_worker.executor import DockerExecutor, MAX_OUTPUT_BYTES, build_docker_command

IMAGE = "ghcr.io/example/worker@sha256:" + "a" * 64


def task(**overrides):
    data = {
        "task_id": "task-1", "image": IMAGE, "command": ["python", "-c", "print('ok')"],
        "cpu_millicores": 500, "memory_mb": 256, "timeout_seconds": 20,
    }
    data.update(overrides)
    return data


def test_docker_command_enforces_isolation_and_resource_limits():
    command = build_docker_command(task(), "ucf-task-test")
    joined = " ".join(command)
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--pids-limit=64" in command
    assert "--memory=256m" in command
    assert "--memory-swap=256m" in command
    assert "--cpus=0.500" in command
    assert "--user=65532:65532" in command
    assert not any(item.startswith("--volume") or item == "-v" for item in command)
    assert command[-4:] == [IMAGE, "python", "-c", "print('ok')"]
    assert "--privileged" not in command


def test_docker_command_rejects_mutable_image_tags():
    try:
        build_docker_command(task(image="python:3.12"), "ucf-task-test")
    except ValueError as exc:
        assert "SHA-256 digest" in str(exc)
    else:
        raise AssertionError("Mutable image tag must be rejected")


def test_executor_rejects_images_outside_allowlist():
    executor = DockerExecutor({IMAGE})
    result = executor.execute(task(image="ghcr.io/other/image@sha256:" + "b" * 64))
    assert result.status == "failed"
    assert result.exit_code == 126
    assert "allowlist" in result.error


def test_executor_requires_an_image_allowlist():
    try:
        DockerExecutor(set())
    except ValueError as exc:
        assert "allowlisted" in str(exc)
    else:
        raise AssertionError("Empty allowlist must be rejected")


def test_output_limit_is_bounded():
    assert MAX_OUTPUT_BYTES == 65536

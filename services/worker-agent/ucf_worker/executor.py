from __future__ import annotations

import hashlib
import re
import subprocess
import threading
from dataclasses import dataclass
from typing import Any

MAX_OUTPUT_BYTES = 64 * 1024
_IMAGE_DIGEST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:@-]{1,254}@sha256:[a-f0-9]{64}$")


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    exit_code: int
    stdout: str
    stderr: str
    error: str | None = None


def build_docker_command(task: dict[str, Any], container_name: str) -> list[str]:
    image = task.get("image", "")
    command = task.get("command")
    cpu_millicores = int(task.get("cpu_millicores", 0))
    memory_mb = int(task.get("memory_mb", 0))
    timeout_seconds = int(task.get("timeout_seconds", 0))
    if not isinstance(image, str) or not _IMAGE_DIGEST.fullmatch(image):
        raise ValueError("Task image must be pinned to a SHA-256 digest")
    if not isinstance(command, list) or not command or any(
        not isinstance(arg, str) or not arg or len(arg) > 4096 for arg in command
    ):
        raise ValueError("Task command must be a non-empty argument array")
    if cpu_millicores < 100 or memory_mb < 64 or not 1 <= timeout_seconds <= 300:
        raise ValueError("Task resource limits are outside the supported range")

    cpu_limit = f"{cpu_millicores / 1000:.3f}"
    return [
        "docker", "run", "--rm", "--pull=never", "--name", container_name,
        "--network=none", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=64",
        f"--memory={memory_mb}m", f"--memory-swap={memory_mb}m",
        f"--cpus={cpu_limit}", "--user=65532:65532",
        "--workdir=/tmp",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m,uid=65532,gid=65532",
        "--shm-size=16m", "--ulimit=nofile=256:256",
        "--log-driver=none", image, *command,
    ]


class DockerExecutor:
    """Runs pre-approved, digest-pinned OCI images with a restrictive Docker profile."""

    def __init__(self, allowed_images: set[str]):
        self.allowed_images = frozenset(allowed_images)
        if not self.allowed_images or any(not _IMAGE_DIGEST.fullmatch(item) for item in self.allowed_images):
            raise ValueError("At least one valid digest-pinned image must be allowlisted")

    @staticmethod
    def _container_name(task_id: str) -> str:
        digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:20]
        return f"ucf-task-{digest}"

    @staticmethod
    def _drain(stream, target: bytearray) -> None:
        while True:
            chunk = stream.read(4096)
            if not chunk:
                return
            remaining = MAX_OUTPUT_BYTES - len(target)
            if remaining > 0:
                target.extend(chunk[:remaining])

    def execute(self, task: dict[str, Any]) -> ExecutionResult:
        image = task.get("image")
        if image not in self.allowed_images:
            return ExecutionResult("failed", 126, "", "", "Image is not in the worker allowlist")
        task_id = str(task.get("task_id", ""))
        container_name = self._container_name(task_id)
        try:
            command = build_docker_command(task, container_name)
        except (TypeError, ValueError) as exc:
            return ExecutionResult("failed", 126, "", "", str(exc))

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as exc:
            return ExecutionResult("failed", 127, "", "", f"Docker runtime unavailable: {exc}")

        stdout = bytearray()
        stderr = bytearray()
        readers = [
            threading.Thread(target=self._drain, args=(process.stdout, stdout), daemon=True),
            threading.Thread(target=self._drain, args=(process.stderr, stderr), daemon=True),
        ]
        for reader in readers:
            reader.start()
        timeout_seconds = int(task["timeout_seconds"])
        try:
            exit_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["docker", "kill", container_name],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False,
            )
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            for reader in readers:
                reader.join(timeout=2)
            return ExecutionResult(
                "failed", 124, stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"), "Task execution timed out",
            )
        for reader in readers:
            reader.join(timeout=2)
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        return ExecutionResult("succeeded" if exit_code == 0 else "failed", exit_code, out, err)

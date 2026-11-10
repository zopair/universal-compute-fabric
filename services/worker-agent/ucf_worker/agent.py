from __future__ import annotations

import json
import logging
import os
import re
import signal
import shutil
import subprocess
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

import psutil

from ucf_worker.executor import DockerExecutor

LOG = logging.getLogger("ucf-worker")


def validate_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("UCF_CONTROL_PLANE_URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("UCF_CONTROL_PLANE_URL must not contain credentials, query or fragment")
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Remote control-plane connections must use HTTPS")
    return endpoint.rstrip("/")


def collect_resources(gpu_units: int | None = None) -> dict[str, object]:
    cpu_count = psutil.cpu_count(logical=True) or 1
    cpu_utilization = psutil.cpu_percent(interval=0.1)
    total_cpu_millicores = cpu_count * 1000
    available_memory_mb = psutil.virtual_memory().available // (1024 * 1024)
    resources: dict[str, object] = {
        "available_cpu_millicores": max(
            0, int(total_cpu_millicores * (100.0 - cpu_utilization) / 100.0)
        ),
        "available_memory_mb": max(0, available_memory_mb),
    }
    # Preserve admin-declared capabilities unless GPU inventory is explicitly configured.
    if gpu_units is not None:
        resources["gpu_units"] = gpu_units
    return resources


def post_json(endpoint: str, path: str, token: str, payload: dict[str, object] | None = None,
              timeout: int = 10) -> dict[str, object]:
    request = Request(
        f"{endpoint}{path}",
        data=json.dumps(payload or {}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "ucf-worker-agent/0.2",
        },
        method="POST",
    )

    class RejectRedirects(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, new_url):
            return None

    with build_opener(RejectRedirects).open(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Control-plane request returned HTTP {response.status}")
        data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError("Control-plane response must be a JSON object")
        return data


def send_heartbeat(endpoint: str, node_id: str, token: str, payload: dict[str, object],
                   timeout: int = 10) -> None:
    post_json(endpoint, f"/v1/nodes/{node_id}/heartbeat", token, payload, timeout)


def execute_one_task(endpoint: str, token: str, executor: DockerExecutor) -> bool:
    response = post_json(endpoint, "/v1/worker/tasks/claim", token)
    task = response.get("task")
    if task is None:
        return False
    if not isinstance(task, dict) or not isinstance(task.get("task_id"), str):
        raise RuntimeError("Control plane returned an invalid task claim")
    result = executor.execute(task)
    completion = {
        "status": result.status,
        "exit_code": result.exit_code,
        "result": result.stdout,
        "error": (result.error or result.stderr or None)[:8192] if (result.error or result.stderr) else None,
    }
    post_json(endpoint, f"/v1/worker/tasks/{task['task_id']}/complete", token, completion)
    LOG.info("Task %s finished with status %s", task["task_id"], result.status)
    return True


def run() -> None:
    endpoint = validate_endpoint(os.environ["UCF_CONTROL_PLANE_URL"])
    node_id = os.environ["UCF_NODE_ID"]
    token = os.environ["UCF_NODE_TOKEN"]
    interval = int(os.getenv("UCF_HEARTBEAT_INTERVAL_SECONDS", "15"))
    gpu_value = os.getenv("UCF_GPU_UNITS")
    gpu_units = int(gpu_value) if gpu_value is not None else None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", node_id):
        raise ValueError("UCF_NODE_ID contains unsupported characters or has an invalid length")
    if interval < 5 or interval > 300:
        raise ValueError("UCF_HEARTBEAT_INTERVAL_SECONDS must be between 5 and 300")
    if gpu_units is not None and gpu_units < 0:
        raise ValueError("UCF_GPU_UNITS cannot be negative")

    executor = None
    if os.getenv("UCF_EXECUTION_ENABLED", "false").lower() == "true":
        allowed_images = {
            item.strip() for item in os.getenv("UCF_ALLOWED_IMAGE_DIGESTS", "").split(",")
            if item.strip()
        }
        executor = DockerExecutor(allowed_images)
        if shutil.which("docker") is None:
            raise ValueError("Docker CLI is required when UCF_EXECUTION_ENABLED=true")
        probe = subprocess.run(
            ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=10, check=False,
        )
        if probe.returncode != 0:
            raise ValueError("Docker daemon is not available to the worker agent")

    stop = threading.Event()

    def shutdown(signum, _frame):
        LOG.info("Received signal %s; stopping worker agent", signum)
        stop.set()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    backoff = 2
    while not stop.is_set():
        try:
            send_heartbeat(endpoint, node_id, token, collect_resources(gpu_units))
            LOG.info("Heartbeat accepted for node %s", node_id)
            if executor is not None:
                execute_one_task(endpoint, token, executor)
            backoff = 2
            stop.wait(interval)
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
            LOG.warning("Heartbeat failed (%s); retrying in %s seconds", type(exc).__name__, backoff)
            stop.wait(backoff)
            backoff = min(backoff * 2, interval)


def main() -> None:
    logging.basicConfig(
        level=os.getenv("UCF_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        run()
    except KeyError as exc:
        raise SystemExit(f"Missing required environment variable: {exc.args[0]}") from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import logging
import os
import signal
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import psutil

LOG = logging.getLogger("ucf-worker")


def validate_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("UCF_CONTROL_PLANE_URL must be an absolute HTTP(S) URL")
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Remote control-plane connections must use HTTPS")
    return endpoint.rstrip("/")


def collect_resources(gpu_units: int = 0) -> dict[str, object]:
    cpu_count = psutil.cpu_count(logical=True) or 1
    capabilities = ["cpu", "memory", "network"]
    if gpu_units > 0:
        capabilities.append("gpu")
    return {
        "cpu_millicores": cpu_count * 1000,
        "memory_mb": max(1, psutil.virtual_memory().total // (1024 * 1024)),
        "gpu_units": gpu_units,
        "capabilities": capabilities,
    }


def send_heartbeat(endpoint: str, node_id: str, token: str, payload: dict[str, object], timeout: int = 10) -> None:
    url = f"{endpoint}/v1/nodes/{node_id}/heartbeat"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "ucf-worker-agent/0.1",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Heartbeat returned HTTP {response.status}")


def run() -> None:
    endpoint = validate_endpoint(os.environ["UCF_CONTROL_PLANE_URL"])
    node_id = os.environ["UCF_NODE_ID"]
    token = os.environ["UCF_NODE_TOKEN"]
    interval = int(os.getenv("UCF_HEARTBEAT_INTERVAL_SECONDS", "15"))
    gpu_units = int(os.getenv("UCF_GPU_UNITS", "0"))
    if not node_id or len(node_id) > 128:
        raise ValueError("UCF_NODE_ID must contain 1 to 128 characters")
    if interval < 5 or interval > 300:
        raise ValueError("UCF_HEARTBEAT_INTERVAL_SECONDS must be between 5 and 300")
    if gpu_units < 0:
        raise ValueError("UCF_GPU_UNITS cannot be negative")

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
            backoff = 2
            stop.wait(interval)
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as exc:
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

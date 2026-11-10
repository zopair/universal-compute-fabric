import pytest

from ucf_worker.agent import collect_resources, validate_endpoint


def test_remote_endpoint_requires_tls():
    with pytest.raises(ValueError):
        validate_endpoint("http://compute.example.com")


def test_local_http_is_allowed():
    assert validate_endpoint("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"


def test_resources_include_gpu_capability_when_declared():
    resources = collect_resources(gpu_units=1)
    assert resources["cpu_millicores"] > 0
    assert resources["memory_mb"] > 0
    assert "gpu" in resources["capabilities"]

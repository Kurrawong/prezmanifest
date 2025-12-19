import time
from pathlib import Path

import docker
import httpx
import pytest
from kurra.sparql import query
from testcontainers.core.container import DockerContainer

FUSEKI_IMAGE = "ghcr.io/kurrawong/fuseki-geosparql:git-main-e642d849"


def wait_for_logs(container, text, timeout=30, interval=0.5):
    """
    Wait until the container emits a log line containing `text`.
    """
    client = docker.from_env()
    start_time = time.time()

    logs_seen = ""

    while True:
        # Read logs incrementally
        logs = client.containers.get(container._container.id).logs().decode("utf-8")
        if text in logs:
            return True

        if time.time() - start_time > timeout:
            raise TimeoutError(f"Timed out waiting for log: {text}")

        time.sleep(interval)


@pytest.fixture(scope="session")
def fuseki_container():
    container = DockerContainer(FUSEKI_IMAGE)
    container.with_volume_mapping(
        str(Path(__file__).parent / "fuseki" / "shiro.ini"),
        "/fuseki/shiro.ini",
    )
    container.with_volume_mapping(
        str(Path(__file__).parent / "fuseki" / "config.ttl"),
        "/fuseki/config.ttl",
    )
    container.with_exposed_ports(3030)
    container.start()
    wait_for_logs(container, "Started")

    yield container
    container.stop()


@pytest.fixture(scope="function")
def sparql_endpoint(fuseki_container):
    url = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"
    yield url
    with httpx.Client(auth=("admin", "admin")) as http_client:
        query(url, "DROP ALL", http_client=http_client)


@pytest.fixture(scope="function")
def http_client():
    _http_client = httpx.Client(auth=("admin", "admin"))

    yield _http_client
    _http_client.close()

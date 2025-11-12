from pathlib import Path

import httpx
import pytest
from testcontainers.compose import DockerCompose

from prezmanifest.syncer import DeltaEventClient

DELTA_PORT = 9999
FUSEKI_PORT = 9998
filepath = Path(__file__).parent.resolve()
compose = DockerCompose(str(filepath))


@pytest.fixture(autouse=True)
def setup():
    compose.start()
    compose.wait_for(f"http://localhost:{FUSEKI_PORT}/ds")
    yield
    compose.stop()


@pytest.fixture
def client():
    _client = DeltaEventClient(f"http://localhost:{DELTA_PORT}", "ds")
    yield _client
    _client._inner.close()


@pytest.fixture
def http_client():
    with httpx.Client() as _client:
        yield _client


@pytest.fixture
def sparql_endpoint():
    return f"http://localhost:{FUSEKI_PORT}/ds"

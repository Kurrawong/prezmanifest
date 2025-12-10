from pathlib import Path

import pytest
from testcontainers.compose import DockerCompose
from testcontainers.core.waiting_utils import wait_for_logs

FUSEKI_PORT = 9998
filepath = Path(__file__).parent.resolve()
compose = DockerCompose(str(filepath))


@pytest.fixture(autouse=True)
def setup():
    compose.start()
    compose.wait_for(f"http://localhost:{FUSEKI_PORT}/ds")
    wait_for_logs(
        compose.get_container("emulator"), "Emulator Service is Successfully Up!"
    )
    yield
    compose.stop()


@pytest.fixture
def connection_string():
    # Azure Service Bus emulator connection string format
    # The emulator typically accepts any key
    # return "Endpoint=sb://localhost:5672/gswa;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=test-key"
    return "Endpoint=sb://localhost;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=SAS_KEY_VALUE;UseDevelopmentEmulator=true;"


@pytest.fixture
def topic():
    return "rdf-delta"


@pytest.fixture
def subscription():
    return "event-persistence-consumer"


@pytest.fixture
def session():
    return "test-session"


@pytest.fixture
def sparql_endpoint():
    return f"http://localhost:{FUSEKI_PORT}/ds"

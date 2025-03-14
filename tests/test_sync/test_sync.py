from pathlib import Path
from typer.testing import CliRunner
from prezmanifest.syncer import sync
from tests.fuseki.conftest import fuseki_container
from kurra.db import sparql, upload
from prezmanifest.loader import load
from prezmanifest.utils import artifact_file_name_from_graph_id
import json
runner = CliRunner()


def test_sync(fuseki_container):
    SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"
    MANIFEST_FILE_LOCAL = Path(__file__).parent / "local/manifest.ttl"
    MANIFEST_FILE_REMOTE = Path(__file__).parent / "remote/manifest.ttl"
    MANIFEST_ROOT = Path(__file__).parent / "local"

    # ensure the store's clear
    sparql(SPARQL_ENDPOINT, "DROP ALL")

    # load it with remote data
    load(MANIFEST_FILE_REMOTE, SPARQL_ENDPOINT)

    a = json.loads(sync(
        MANIFEST_FILE_LOCAL,
        SPARQL_ENDPOINT,
        None,
    ))

    print(a)
    exit()
    assert a[str(MANIFEST_ROOT / "artifacts/artifact1.ttl")]["direction"] == "unchanged"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact2.ttl")]["direction"] == "forward"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact3.ttl")]["direction"] == "forward"
    assert a[str(MANIFEST_ROOT / "artifact4.ttl")]["direction"] == "forward"
    assert a[str(MANIFEST_ROOT / "artifact5.ttl")]["direction"] == "missing-remotely"
    assert a[str(MANIFEST_ROOT / "artifact6.ttl")]["direction"] == "reverse"
    assert a[str(MANIFEST_ROOT / "artifact7.ttl")]["direction"] == "forward"
    assert a["http://example.com/dataset/8"]["direction"] == "missing-locally"
    assert a[str(MANIFEST_ROOT / "catalogue.ttl")]["direction"] == "unchanged"

    a = json.loads(sync(
        MANIFEST_FILE_LOCAL,
        SPARQL_ENDPOINT,
        None,
        False, False, False, False
    ))

    assert a[str(MANIFEST_ROOT / "artifacts/artifact1.ttl")]["direction"] == "unchanged"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact2.ttl")]["direction"] == "unchanged"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact3.ttl")]["direction"] == "unchanged"
    assert a[str(MANIFEST_ROOT / "artifact4.ttl")]["direction"] == "unchanged"
    assert a[str(MANIFEST_ROOT / "artifact5.ttl")]["direction"] == "unchanged"
    assert a[str(MANIFEST_ROOT / "artifact6.ttl")]["direction"] == "unchanged"
    assert a[str(MANIFEST_ROOT / "artifact7.ttl")]["direction"] == "unchanged"
    assert a[str(MANIFEST_ROOT / artifact_file_name_from_graph_id("http://example.com/dataset/8"))]["direction"] == "unchanged"
    assert a[str(MANIFEST_ROOT / "catalogue.ttl")]["direction"] == "unchanged"


def test_sync_cli():
    pass
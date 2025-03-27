import json
import shutil
from pathlib import Path

from kurra.db import sparql
from typer.testing import CliRunner

from prezmanifest.loader import load
from prezmanifest.syncer import sync
from prezmanifest.utils import artifact_file_name_from_graph_id
from tests.fuseki.conftest import fuseki_container

runner = CliRunner(mix_stderr=False)
from prezmanifest.cli import app


def test_sync(fuseki_container):
    SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"
    MANIFEST_FILE_LOCAL = Path(__file__).parent / "local/manifest.ttl"
    MANIFEST_FILE_REMOTE = Path(__file__).parent / "remote/manifest.ttl"
    MANIFEST_ROOT = Path(__file__).parent / "local"

    # make copies of files that will be overwritten
    shutil.copy(MANIFEST_FILE_LOCAL, MANIFEST_FILE_LOCAL.with_suffix(".ttx"))
    shutil.copy(MANIFEST_ROOT / "catalogue.ttl", MANIFEST_ROOT / "catalogue.ttx")
    shutil.copy(MANIFEST_ROOT / "artifact6.ttl", MANIFEST_ROOT / "artifact6.ttx")

    # ensure the SPARQL store's clear
    sparql(SPARQL_ENDPOINT, "DROP ALL")

    # load it with remote data
    load(MANIFEST_FILE_REMOTE, SPARQL_ENDPOINT)

    a = sync(
        MANIFEST_FILE_LOCAL,
        SPARQL_ENDPOINT,
    )

    # check status before sync
    assert a[str(MANIFEST_ROOT / "artifacts/artifact1.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact2.ttl")]["direction"] == "upload"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact3.ttl")]["direction"] == "upload"
    assert a[str(MANIFEST_ROOT / "artifact4.ttl")]["direction"] == "upload"
    assert a[str(MANIFEST_ROOT / "artifact5.ttl")]["direction"] == "add-remotely"
    assert a[str(MANIFEST_ROOT / "artifact6.ttl")]["direction"] == "download"
    assert a[str(MANIFEST_ROOT / "artifact7.ttl")]["direction"] == "upload"
    assert a["http://example.com/dataset/8"]["direction"] == "add-locally"
    assert a[str(MANIFEST_ROOT / "catalogue.ttl")]["direction"] == "same"

    # run sync again, performing no actions to just get updated status
    a = sync(MANIFEST_FILE_LOCAL, SPARQL_ENDPOINT, None, False, False, False, False)

    # check status after sync
    assert a[str(MANIFEST_ROOT / "artifacts/artifact1.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact2.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact3.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact4.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact5.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact6.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact7.ttl")]["direction"] == "same"
    assert (
        a[
            str(
                MANIFEST_ROOT
                / artifact_file_name_from_graph_id("http://example.com/dataset/8")
            )
        ]["direction"]
        == "same"
    )
    assert a[str(MANIFEST_ROOT / "catalogue.ttl")]["direction"] == "same"

    # tidy up
    shutil.move(MANIFEST_ROOT / "manifest.ttx", MANIFEST_FILE_LOCAL)
    shutil.move(MANIFEST_ROOT / "catalogue.ttx", MANIFEST_ROOT / "catalogue.ttl")
    shutil.move(MANIFEST_ROOT / "artifact6.ttx", MANIFEST_ROOT / "artifact6.ttl")
    Path(MANIFEST_ROOT / "http--example.com-dataset-8.ttl").unlink()


def test_sync_cli(fuseki_container):
    MANIFEST_FILE_REMOTE = Path(__file__).parent / "remote/manifest.ttl"
    SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"

    # ensure the SPARQL store's clear
    sparql(SPARQL_ENDPOINT, "DROP ALL")

    raw_output = str(
        runner.invoke(
            app, ["sync", str(MANIFEST_FILE_REMOTE), SPARQL_ENDPOINT, "-f", "json"]
        ).stdout
    )

    r = json.loads(raw_output)

    assert str(MANIFEST_FILE_REMOTE.parent / "catalogue.ttl") in r.keys()

    # test cli pretty formatting
    raw_output = str(
        runner.invoke(app, ["sync", str(MANIFEST_FILE_REMOTE), SPARQL_ENDPOINT]).stdout
    )
    assert "Main Entity" in raw_output

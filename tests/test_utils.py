from pathlib import Path

import kurra.db
import pytest
from kurra.db import sparql, upload
from kurra.file import export_quads
from kurra.utils import load_graph
from typer.testing import CliRunner
from datetime import datetime
from prezmanifest.utils import *
from tests.fuseki.conftest import fuseki_container

runner = CliRunner()
import httpx

TESTS_DIR = Path(__file__).resolve().parent


def test_path_or_url():
    s1 = "http://example.com"
    assert path_or_url(s1) == s1

    s2 = "/usr/local"
    assert path_or_url(s2) == Path(s2)


def test_localise_path():
    p = Path("/usr/lib/some-file.txt")
    r = Path("/usr/lib")

    x = localise_path(p, r)

    assert x == Path("some-file.txt")

    p = "/usr/lib/some-file.txt"
    r = Path("/usr/lib")

    x = localise_path(p, r)

    assert x == Path("some-file.txt")

    p = "http://example.com/file/one.txt"
    r = Path("/usr/lib")

    x = localise_path(p, r)

    assert x == p


def test_absolutise_path():
    p = Path("some-file.txt")
    r = Path("/usr/lib")

    x = absolutise_path(p, r)

    assert x == Path("/usr/lib/some-file.txt")

    p = "http://example.com/file/one.txt"
    r = Path("/usr/lib")

    x = absolutise_path(p, r)

    assert x == p


def test_get_files_from_artifact():
    MANIFEST = TESTS_DIR / "demo-vocabs" / "manifest.ttl"

    fs = list(
        get_files_from_artifact(
        MANIFEST,
        Literal("vocabs/*.ttl")
    ))


    assert len(fs) == 2
    assert Path("/Users/nick/work/kurrawong/prez-manifest/tests/demo-vocabs/vocabs/image-test.ttl") in fs
    assert Path("/Users/nick/work/kurrawong/prez-manifest/tests/demo-vocabs/vocabs/language-test.ttl") in fs


def test_get_identifier_from_file():
    f1 = TESTS_DIR / "demo-vocabs" / "vocabs" / "image-test.ttl"

    i = get_identifier_from_file(f1)
    assert i[0] == URIRef("https://example.com/demo-vocabs/image-test")


def test_get_validator_graph():
    MANIFEST = TESTS_DIR / "demo-vocabs" / "manifest.ttl"

    g = get_validator_graph(MANIFEST, URIRef("https://data.idnau.org/pid/cp"))

    assert len(g) == 318

    g2 = get_validator_graph(
        MANIFEST,
        TESTS_DIR / "demo-vocabs" / "vocabs" / "image-test.ttl"
    )

    assert len(g2) == 29


# TODO
def test_get_manifest_paths_and_graph():
    pass


def test_get_catalogue_iri_from_manifest():
    pass


# TODO
def test_does_target_contain_this_catalogue():
    pass


# TODO
def test_make_httpx_client():
    pass


# TODO
def test_get_main_entity_iri_via_conformance_claims():
    pass


def test_get_version_indicators_for_artifact():
    MANIFEST = TESTS_DIR / "demo-vocabs" / "manifest.ttl"

    orig = get_version_indicators_for_artifact(
        MANIFEST,
        TESTS_DIR / "demo-vocabs" / "vocabs" / "language-test.ttl"
    )

    assert orig["modified_date"] == datetime.strptime("2024-11-21", "%Y-%m-%d")

    v1 = get_version_indicators_for_artifact(
        MANIFEST,
        TESTS_DIR / "demo-vocabs-updated1" / "vocabs" / "language-test.ttl",
        URIRef("https://example.com/demo-vocabs/language-test")
    )

    assert v1["modified_date"] == datetime.strptime("2025-02-28", "%Y-%m-%d")

    v5 = get_version_indicators_for_artifact(
        MANIFEST,
        TESTS_DIR / "demo-vocabs-updated5" / "vocabs" / "language-test.ttl"
    )

    assert v5["modified_date"] == datetime.strptime("2025-02-28", "%Y-%m-%d")

    assert v5["version_iri"] == "https://example.com/demo-vocabs/language-test/1.1"

    with pytest.raises(ValueError):
        v6 = get_version_indicators_for_artifact(
            MANIFEST,
            TESTS_DIR / "demo-vocabs-updated6" / "vocabs" / "language-test.ttl"
        )


def test_get_version_indicators_for_graph_in_sparql_endpoint(fuseki_container):
    port = fuseki_container.get_exposed_port(3030)
    SPARQL_ENDPOINT = f"http://localhost:{port}/ds"
    ASSET_PATH = TESTS_DIR / "demo-vocabs" / "vocabs" / "language-test.ttl"
    ASSET_GRAPH_IRI = "https://example.com/demo-vocabs/language-test"

    c = make_httpx_client()

    upload(
        SPARQL_ENDPOINT,
        ASSET_PATH,
        ASSET_GRAPH_IRI,
        False,
        http_client=c
    )

    q = """
        SELECT (COUNT(*) AS ?count) 
        WHERE {
          GRAPH <XXX> {
            ?s ?p ?o
          }
        }        
        """.replace("XXX", ASSET_GRAPH_IRI)

    r = sparql(SPARQL_ENDPOINT, q, c, return_python=True, return_bindings_only=True)

    count = int(r[0]["count"]["value"])

    assert count == 77

    r = get_version_indicators_for_graph_in_sparql_endpoint(
        ASSET_GRAPH_IRI,
        SPARQL_ENDPOINT,
        http_client=c
    )

    assert r["modified_date"] == datetime.strptime("2024-11-21", "%Y-%m-%d")


def test_first_is_more_recent_than_second_using_version_indicators():
    one = {
        "modified_date": datetime.strptime("2024-11-20", "%Y-%m-%d"),
        "version": None,
        "version_iri": None,
        "file_size": None,
        "main_entity_iri": None,
    }

    two = {
        "modified_date": datetime.strptime("2024-11-21", "%Y-%m-%d"),
        "version": "1.1",
        "version_iri": None,
        "file_size": None,
        "main_entity_iri": None,
    }

    assert not first_is_more_recent_than_second_using_version_indicators(one, two)

    three = {
        "modified_date": None,
        "version": "1.2.2",
        "version_iri": None,
        "file_size": None,
        "main_entity_iri": None,
    }

    assert not first_is_more_recent_than_second_using_version_indicators(two, three)

    four = {
        "modified_date": None,
        "version": "1.2.3",
        "version_iri": None,
        "file_size": None,
        "main_entity_iri": None,
    }

    assert not first_is_more_recent_than_second_using_version_indicators(three, four)

    five = {
        "modified_date": None,
        "version": None,
        "version_iri": "https://example.com/demo-vocabs/language-test/1",
        "file_size": None,
        "main_entity_iri": None,
    }

    six = {
        "modified_date": None,
        "version": None,
        "version_iri": "https://example.com/demo-vocabs/language-test/2.0",
        "file_size": None,
        "main_entity_iri": None,
    }

    assert not first_is_more_recent_than_second_using_version_indicators(five, six)

    seven = {
        "modified_date": None,
        "version": None,
        "version_iri": "https://example.com/demo-vocabs/language-test/2.1",
        "file_size": None,
        "main_entity_iri": None,
    }

    assert not first_is_more_recent_than_second_using_version_indicators(six, seven)


def test_local_artifact_is_more_recent_then_stored_data(fuseki_container):
    port = fuseki_container.get_exposed_port(3030)
    MANIFEST = TESTS_DIR / "demo-vocabs-updated1" / "manifest.ttl"
    SPARQL_ENDPOINT = f"http://localhost:{port}/ds"
    ASSET_PATH = TESTS_DIR / "demo-vocabs" / "vocabs" / "language-test.ttl"
    ASSET_GRAPH_IRI = "https://example.com/demo-vocabs/language-test"

    c = make_httpx_client()

    upload(
        SPARQL_ENDPOINT,
        ASSET_PATH,
        ASSET_GRAPH_IRI,
        False,
        c
    )

    # r = get_version_indicators_for_graph_in_sparql_endpoint(
    #     ASSET_GRAPH_IRI,
    #     SPARQL_ENDPOINT,
    #     http_client=c
    # )
    #
    # assert r["modified_date"] == datetime.strptime("2024-11-21", "%Y-%m-%d")

    r = local_artifact_is_more_recent_then_stored_data(
        MANIFEST,
        TESTS_DIR / "demo-vocabs-updated1" / "vocabs" / "language-test.ttl",
        SPARQL_ENDPOINT,
        c
    )

    assert r


def test_denormalise_artifacts():
    m = TESTS_DIR / "demo-vocabs" / "manifest-conformance.ttl"
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(m)

    x = denormalise_artifacts((manifest_path, manifest_root, manifest_graph))
    assert len(x) == 5
    artifacts = []
    for xx in x:
        artifacts.append(xx[0])
    assert Path("catalogue.ttl") in artifacts
    assert Path("vocabs/image-test.ttl") in artifacts
    assert Path("vocabs/language-test.ttl") in artifacts
    assert "https://raw.githubusercontent.com/RDFLib/prez/refs/heads/main/prez/reference_data/profiles/ogc_records_profile.ttl" in artifacts
    assert Path("_background/labels.ttl") in artifacts

    m = TESTS_DIR / "demo-vocabs" / "manifest.ttl"
    x = denormalise_artifacts(m)
    assert len(x) == 5
    artifacts = []
    for xx in x:
        artifacts.append(xx[0])
    assert Path("catalogue.ttl") in artifacts
    assert Path("vocabs/image-test.ttl") in artifacts
    assert Path("vocabs/language-test.ttl") in artifacts
    assert "https://raw.githubusercontent.com/RDFLib/prez/refs/heads/main/prez/reference_data/profiles/ogc_records_profile.ttl" in artifacts
    assert Path("_background/labels.ttl") in artifacts

    m = TESTS_DIR / "demo-vocabs" / "manifest-conformance-all.ttl"
    x = denormalise_artifacts(m)
    artifacts = []
    for xx in x:
        artifacts.append(xx[0])
    assert len(x) == 5
    assert Path("catalogue.ttl") in artifacts
    assert Path("vocabs/image-test.ttl") in artifacts
    assert Path("vocabs/language-test.ttl") in artifacts
    assert "https://raw.githubusercontent.com/RDFLib/prez/refs/heads/main/prez/reference_data/profiles/ogc_records_profile.ttl" in artifacts
    assert Path("_background/labels.ttl") in artifacts

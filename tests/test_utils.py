from datetime import datetime

import pytest
from kurra.db import upload
from typer.testing import CliRunner

import prezmanifest.loader
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

    fs = list(get_files_from_artifact(MANIFEST, Literal("vocabs/*.ttl")))

    assert len(fs) == 2
    assert (
        Path(
            "/Users/nick/work/kurrawong/prez-manifest/tests/demo-vocabs/vocabs/image-test.ttl"
        )
        in fs
    )
    assert (
        Path(
            "/Users/nick/work/kurrawong/prez-manifest/tests/demo-vocabs/vocabs/language-test.ttl"
        )
        in fs
    )


def test_get_identifier_from_file():
    f1 = TESTS_DIR / "demo-vocabs" / "vocabs" / "image-test.ttl"

    i = get_identifier_from_file(f1)
    assert i[0] == URIRef("https://example.com/demo-vocabs/image-test")


def test_get_validator_graph():
    MANIFEST = TESTS_DIR / "demo-vocabs" / "manifest.ttl"

    g = get_validator_graph(MANIFEST, URIRef("https://data.idnau.org/pid/cp"))

    assert len(g) == 318

    g2 = get_validator_graph(
        MANIFEST, TESTS_DIR / "demo-vocabs" / "vocabs" / "image-test.ttl"
    )

    assert len(g2) == 29


def test_get_manifest_paths_and_graph():
    MANIFEST = TESTS_DIR / "demo-vocabs" / "manifest.ttl"

    extracted_file_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        MANIFEST
    )

    assert extracted_file_path == MANIFEST
    assert manifest_root == MANIFEST.parent
    assert len(manifest_graph) == 21


def test_get_catalogue_iri_from_manifest():
    MANIFEST = TESTS_DIR / "demo-vocabs" / "manifest.ttl"

    assert get_catalogue_iri_from_manifest(MANIFEST) == URIRef(
        "https://example.com/demo-vocabs"
    )


def test_target_contains_this_manifests_catalogue(fuseki_container):
    MANIFEST = TESTS_DIR / "demo-vocabs" / "manifest.ttl"
    port = fuseki_container.get_exposed_port(3030)

    with httpx.Client() as client:
        SPARQL_ENDPOINT = f"http://localhost:{port}/ds"

        # positive test
        sparql(SPARQL_ENDPOINT, "DROP ALL", client)
        prezmanifest.loader.load(MANIFEST, SPARQL_ENDPOINT)
        assert target_contains_this_manifests_catalogue(MANIFEST, SPARQL_ENDPOINT)

        # negative test
        sparql(SPARQL_ENDPOINT, "DROP ALL", client)
        assert not target_contains_this_manifests_catalogue(MANIFEST, SPARQL_ENDPOINT)


# TODO add tests
def test_make_httpx_client():
    pass


def test_get_main_entity_iri_of_artifact():
    MANIFEST = TESTS_DIR / "demo-vocabs" / "manifest-conformance.ttl"

    assert get_main_entity_iri_of_artifact(
        MANIFEST.parent / "vocabs/image-test.ttl", MANIFEST
    ) == URIRef("https://example.com/demo-vocabs/image-test")

    assert get_main_entity_iri_of_artifact(
        MANIFEST.parent / "vocabs/language-test.ttl", MANIFEST
    ) == URIRef("https://example.com/demo-vocabs/language-test")


def test_get_version_indicators_local():
    MANIFEST = TESTS_DIR / "demo-vocabs" / "manifest.ttl"

    vi = {}
    get_version_indicators_local(
        MANIFEST, TESTS_DIR / "demo-vocabs" / "vocabs" / "language-test.ttl", vi
    )

    assert vi["modified_date"] == date_parse("2024-11-21")
    assert vi["version_iri"] == "https://example.com/demo-vocabs/language-test/1.0"

    with pytest.raises(ValueError):
        vi = {}
        get_version_indicators_local(
            MANIFEST, TESTS_DIR / "demo-vocabs" / "vocabs" / "language-testx.ttl", vi
        )


def test_get_version_indicators_sparql(fuseki_container):
    port = fuseki_container.get_exposed_port(3030)
    SPARQL_ENDPOINT = f"http://localhost:{port}/ds"
    ASSET_PATH = TESTS_DIR / "demo-vocabs" / "vocabs" / "language-test.ttl"
    ASSET_GRAPH_IRI = "https://example.com/demo-vocabs/language-test"

    c = make_httpx_client()

    upload(SPARQL_ENDPOINT, ASSET_PATH, ASSET_GRAPH_IRI, False, http_client=c)

    q = """
        SELECT (COUNT(*) AS ?count) 
        WHERE {
          GRAPH <XXX> {
            ?s ?p ?o
          }
        }        
        """.replace(
        "XXX", ASSET_GRAPH_IRI
    )

    r = query(SPARQL_ENDPOINT, q, c, return_python=True, return_bindings_only=True)

    count = int(r[0]["count"]["value"])

    assert count == 71

    r = get_version_indicators_sparql(ASSET_GRAPH_IRI, SPARQL_ENDPOINT, http_client=c)

    assert r["modified_date"] == date_parse("2024-11-21")


def test_compare_version_indicators():
    one = {
        "modified_date": date_parse("2024-11-20"),
        "version_info": None,
        "version_iri": None,
        "file_size": None,
        "main_entity_iri": None,
    }

    two = {
        "modified_date": date_parse("2024-11-21"),
        "version_info": "1.1",
        "version_iri": None,
        "file_size": None,
        "main_entity_iri": None,
    }

    assert compare_version_indicators(one, two) == VersionIndicatorComparison.Second

    three = {
        "modified_date": None,
        "version_info": "1.2.2",
        "version_iri": None,
        "file_size": None,
        "main_entity_iri": None,
    }

    assert compare_version_indicators(two, three) == VersionIndicatorComparison.Second

    four = {
        "modified_date": None,
        "version_info": "1.2.3",
        "version_iri": None,
        "file_size": None,
        "main_entity_iri": None,
    }

    assert compare_version_indicators(three, four) == VersionIndicatorComparison.Second

    five = {
        "modified_date": None,
        "version_info": None,
        "version_iri": "https://example.com/demo-vocabs/language-test/1",
        "file_size": None,
        "main_entity_iri": None,
    }

    six = {
        "modified_date": None,
        "version_info": None,
        "version_iri": "https://example.com/demo-vocabs/language-test/2.0",
        "file_size": None,
        "main_entity_iri": None,
    }

    assert compare_version_indicators(five, six) == VersionIndicatorComparison.Second

    seven = {
        "modified_date": None,
        "version_info": None,
        "version_iri": "https://example.com/demo-vocabs/language-test/2.1",
        "file_size": None,
        "main_entity_iri": None,
    }

    assert compare_version_indicators(six, seven) == VersionIndicatorComparison.Second


def test_which_is_more_recent(fuseki_container):
    port = fuseki_container.get_exposed_port(3030)
    SPARQL_ENDPOINT = f"http://localhost:{port}/ds"
    ARTIFACT_PATH = TESTS_DIR / "demo-vocabs" / "vocabs" / "language-test.ttl"
    ARTIFACT_MAIN_ENTITY = "https://example.com/demo-vocabs/language-test"

    c = make_httpx_client()

    upload(SPARQL_ENDPOINT, ARTIFACT_PATH, ARTIFACT_MAIN_ENTITY, False, c)

    vi = {
        "main_entity": URIRef("https://example.com/demo-vocabs/language-test"),
        "modified_date": datetime(2025, 2, 28, 0, 0),
        "version_iri": "https://example.com/demo-vocabs/language-test/1.1",
        "file_size": 5053,
    }

    r = which_is_more_recent(vi, SPARQL_ENDPOINT, c)

    assert r == VersionIndicatorComparison.First

    vi2 = {
        "main_entity": URIRef("https://example.com/demo-vocabs/language-test"),
        "modified_date": datetime(2023, 2, 28, 0, 0),
        "file_size": 5053,
    }

    r = which_is_more_recent(vi2, SPARQL_ENDPOINT, c)

    assert r == VersionIndicatorComparison.Second


def test_denormalise_artifacts():
    m = TESTS_DIR / "demo-vocabs" / "manifest-conformance.ttl"
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(m)
    x = denormalise_artifacts((manifest_path, manifest_root, manifest_graph))
    assert manifest_root / "catalogue.ttl" in x.keys()
    assert manifest_root / "vocabs/image-test.ttl" in x.keys()
    assert manifest_root / "vocabs/language-test.ttl" in x.keys()
    assert (
        "https://raw.githubusercontent.com/RDFLib/prez/refs/heads/main/prez/reference_data/profiles/ogc_records_profile.ttl"
        in x.keys()
    )
    assert manifest_root / "_background/labels.ttl" in x.keys()

    assert x[manifest_root / "vocabs/image-test.ttl"]["file_size"] == 20324

    m = TESTS_DIR / "demo-vocabs" / "manifest-conformance-all.ttl"
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(m)
    x = denormalise_artifacts(m)
    assert manifest_root / "catalogue.ttl" in x.keys()
    assert manifest_root / "vocabs/image-test.ttl" in x.keys()
    assert manifest_root / "vocabs/language-test.ttl" in x.keys()
    assert (
        "https://raw.githubusercontent.com/RDFLib/prez/refs/heads/main/prez/reference_data/profiles/ogc_records_profile.ttl"
        in x.keys()
    )
    assert manifest_root / "_background/labels.ttl" in x.keys()

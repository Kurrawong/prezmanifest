import warnings
from pathlib import Path

import httpx
import pytest
from kurra.db import upload, sparql
from rdflib import Dataset, URIRef

try:
    from prezmanifest import load
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).parent.parent.resolve()))
    from prezmanifest import load


def test_load_only_one_set():
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning
    )  # ignore RDFLib's ConjunctiveGraph warning

    manifest_path = Path(Path(__file__).parent / "demo-vocabs/manifest.ttl")

    with pytest.raises(ValueError):
        load(manifest_path)

    with pytest.raises(ValueError):
        load(
            manifest_path,
            sparql_endpoint="http://fake.com",
            destination_file=Path("some-fake-path"),
        )

    with pytest.raises(ValueError):
        load(
            manifest_path,
            destination_file=Path("some-fake-path"),
            return_data_type="Graph",
        )

    load(manifest_path, destination_file=Path("temp.trig"))

    Path("temp.trig").unlink(missing_ok=True)

    try:
        load(manifest_path, return_data_type="hello")
    except ValueError as e:
        assert (
                str(e)
                == "return_data_type was set to an invalid value. Must be one of Dataset or Graph or None"
        )


def test_fuseki_query(fuseki_container):
    port = fuseki_container.get_exposed_port(3030)
    SPARQL_ENDPOINT = f"http://localhost:{port}/ds"
    TESTING_GRAPH = "https://example.com/testing-graph"

    data = """
            PREFIX ex: <http://example.com/>

            ex:a ex:b ex:c .
            ex:a2 ex:b2 ex:c2 .
            """

    upload(SPARQL_ENDPOINT, data, TESTING_GRAPH, False)

    q = """
        SELECT (COUNT(*) AS ?count) 
        WHERE {
          GRAPH <XXX> {
            ?s ?p ?o
          }
        }        
        """.replace(
        "XXX", TESTING_GRAPH
    )

    r = sparql(SPARQL_ENDPOINT, q, return_python=True, return_bindings_only=True)

    count = int(r[0]["count"]["value"])

    assert count == 2

    q = "DROP GRAPH <XXX>".replace("XXX", TESTING_GRAPH)

    print("QUERY")
    print(q)
    print("QUERY")

    r = sparql(SPARQL_ENDPOINT, q)

    print(r)


def test_load_to_quads_file():
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning
    )  # ignore RDFLib's ConjunctiveGraph warning
    manifest = Path(__file__).parent / "demo-vocabs" / "manifest.ttl"
    results_file = Path(__file__).parent / "results.trig"

    # extract all Manifest content into an n-quads file
    load(manifest, sparql_endpoint=None, destination_file=results_file)

    # load the resultant Dataset to test it
    d = Dataset()
    d.parse(results_file, format="trig")

    # get a list of IDs of the Graphs in the Dataset
    graph_ids = [x.identifier for x in d.graphs()]

    # check that each Manifest part has a graph present
    assert URIRef("https://example.com/demo-vocabs-catalogue") in graph_ids
    assert URIRef("https://example.com/demo-vocabs/image-test") in graph_ids
    assert URIRef("https://example.com/demo-vocabs/language-test") in graph_ids
    assert URIRef("http://background") in graph_ids
    assert URIRef("https://olis.dev/SystemGraph") in graph_ids

    Path(results_file).unlink()


def test_load_to_fuseki(fuseki_container):
    SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"

    manifest = Path(__file__).parent / "demo-vocabs" / "manifest.ttl"
    load(manifest, sparql_endpoint=SPARQL_ENDPOINT)

    q = """
        SELECT (COUNT(DISTINCT ?g) AS ?count)
        WHERE {
            GRAPH ?g {
                ?s ?p ?o 
            }
        }      
        """

    r = sparql(SPARQL_ENDPOINT, q, return_python=True, return_bindings_only=True)

    count = int(r[0]["count"]["value"])

    assert count == 5


def test_load_to_fuseki_basic_auth(fuseki_container):
    SPARQL_ENDPOINT = (
        f"http://localhost:{fuseki_container.get_exposed_port(3030)}/authds"
    )

    manifest = Path(__file__).parent / "demo-vocabs" / "manifest.ttl"
    load(
        manifest,
        sparql_endpoint=SPARQL_ENDPOINT,
        sparql_username="admin",
        sparql_password="admin",
    )

    q = """
        SELECT (COUNT(DISTINCT ?g) AS ?count)
        WHERE {
            GRAPH ?g {
                ?s ?p ?o 
            }
        }      
        """
    client = httpx.Client(auth=("admin", "admin"))
    r = sparql(
        SPARQL_ENDPOINT,
        q,
        return_python=True,
        return_bindings_only=True,
        http_client=client,
    )

    count = int(r[0]["count"]["value"])

    assert count == 5


def test_mainclass():
    manifest = Path(__file__).parent / "demo-vocabs" / "cw-manifest.ttl"
    ds = load(manifest=manifest, return_data_type="Dataset")
    named_graphs = [g.identifier for g in ds.graphs()]
    assert URIRef("https://example.com/a") in named_graphs


def test_mainclass_default():
    manifest = Path(__file__).parent / "demo-vocabs" / "cw-manifest-default.ttl"
    ds = load(manifest=manifest, return_data_type="Dataset")
    named_graphs = [g.identifier for g in ds.graphs()]
    assert URIRef("https://example.com/a") in named_graphs


def test_mainclass_invalid():
    manifest = Path(__file__).parent / "demo-vocabs" / "cw-manifest-invalid.ttl"
    with pytest.raises(ValueError, match="Could not determine Resource IRI"):
        ds = load(manifest=manifest, return_data_type="Dataset")

import warnings
from pathlib import Path

import httpx
import pytest
from kurra.db import sparql, upload
from rdflib import Dataset, URIRef
from typer.testing import CliRunner

from prezmanifest.loader import ReturnDatatype, load
from tests.fuseki.conftest import fuseki_container

runner = CliRunner()


def test_load_only_one_set():
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning
    )  # ignore RDFLib's ConjunctiveGraph warning

    manifest = Path(Path(__file__).parent / "demo-vocabs/manifest.ttl")

    with pytest.raises(ValueError):
        load(manifest)

    with pytest.raises(ValueError):
        load(
            manifest,
            sparql_endpoint="http://fake.com",
            destination_file=Path("some-fake-path"),
        )

    with pytest.raises(ValueError):
        load(
            manifest,
            destination_file=Path("some-fake-path"),
            return_data_type=ReturnDatatype.graph,
        )

    with pytest.raises(ValueError):
        load(manifest, return_data_type="hello")

    load(manifest, destination_file=Path("temp.trig"))

    Path("temp.trig").unlink(missing_ok=True)


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

    assert count == 0


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


def test_load_with_artifact_bn():
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning
    )  # ignore RDFLib's ConjunctiveGraph warning
    manifest = Path(__file__).parent / "demo-vocabs" / "manifest-mainEntity.ttl"
    results_file = Path(__file__).parent / "results.trig"

    # extract all Manifest content into an n-quads file
    load(manifest, destination_file=results_file)

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


# TODO: not working
# def test_load_cli_file(fs):
#     warnings.filterwarnings(
#         "ignore", category=DeprecationWarning
#     )  # ignore RDFLib's ConjunctiveGraph warning
#
#     fake_file = fs.create_file(Path(__file__).parent.resolve() / "temp.trig")
#
#     manifest = Path(__file__).parent / "demo-vocabs/manifest.ttl"
#     tmp_output_file = Path(__file__).parent.resolve() / "temp.trig"
#     runner.invoke(
#         app,
#         [
#             "load",
#             "file",
#             manifest,
#             fake_file.path
#         ],
#     )
#
#     output = fake_file.read_text()
#
#     assert output.count(" {") == 5
#
#     # Path("temp.trig").unlink(missing_ok=True)


# TODO: not working
# def test_load_cli_sparql(fuseki_container):
#     warnings.filterwarnings(
#         "ignore", category=DeprecationWarning
#     )  # ignore RDFLib's ConjunctiveGraph warning
#
#     manifest = Path(__file__).parent / "demo-vocabs/manifest.ttl"
#     SPARQL_ENDPOINT = (
#         f"http://localhost:{fuseki_container.get_exposed_port(3030)}/authds"
#     )
#
#     response = runner.invoke(
#         app,
#         [
#             "load",
#             "sparql",
#             manifest,
#             SPARQL_ENDPOINT,
#             "-u",
#             "admin",
#             "-p",
#             "admin"
#         ],
#     )
#
#     print(response.stdout)
#
#     q = """
#         SELECT (COUNT(DISTINCT ?g) AS ?count)
#         WHERE {
#             GRAPH ?g {
#                 ?s ?p ?o
#             }
#         }
#         """
#     client = httpx.Client(auth=("admin", "admin"))
#     r = sparql(
#         SPARQL_ENDPOINT,
#         q,
#         return_python=True,
#         return_bindings_only=True,
#         http_client=client,
#     )
#
#     count = int(r[0]["count"]["value"])
#
#     assert count == 5

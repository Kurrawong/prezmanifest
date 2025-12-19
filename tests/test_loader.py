import warnings
from pathlib import Path

import httpx
import pytest
from kurra.db.gsp import upload
from kurra.sparql import query
from rdflib import Dataset, URIRef
from typer.testing import CliRunner

from prezmanifest.loader import ReturnDatatype, load

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


def test_fuseki_query(sparql_endpoint):
    TESTING_GRAPH = "https://example.com/testing-graph"

    data = """
            PREFIX ex: <http://example.com/>

            ex:a ex:b ex:c .
            ex:a2 ex:b2 ex:c2 .
            """

    upload(sparql_endpoint, data, TESTING_GRAPH, False)

    q = """
        SELECT (COUNT(*) AS ?count) 
        WHERE {
          GRAPH <XXX> {
            ?s ?p ?o
          }
        }        
        """.replace("XXX", TESTING_GRAPH)

    r = query(sparql_endpoint, q, return_format="python", return_bindings_only=True)

    assert r[0]["count"] == 2

    q = "DROP GRAPH <XXX>".replace("XXX", TESTING_GRAPH)

    r = query(sparql_endpoint, q)

    q = """
        SELECT (COUNT(*) AS ?count) 
        WHERE {
          GRAPH <XXX> {
            ?s ?p ?o
          }
        }        
        """.replace("XXX", TESTING_GRAPH)

    r = query(sparql_endpoint, q, return_format="python", return_bindings_only=True)

    assert r[0]["count"] == 0


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


def test_load_to_fuseki(sparql_endpoint):
    manifest = Path(__file__).parent / "demo-vocabs" / "manifest.ttl"
    load(manifest, sparql_endpoint=sparql_endpoint)

    q = """
        SELECT (COUNT(DISTINCT ?g) AS ?count)
        WHERE {
            GRAPH ?g {
                ?s ?p ?o 
            }
        }      
        """

    r = query(sparql_endpoint, q, return_format="python", return_bindings_only=True)

    assert r[0]["count"] == 5


def test_load_to_fuseki_basic_auth(sparql_endpoint):
    manifest = Path(__file__).parent / "demo-vocabs" / "manifest.ttl"
    load(
        manifest,
        sparql_endpoint=sparql_endpoint,
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
    r = query(
        sparql_endpoint,
        q,
        return_format="python",
        return_bindings_only=True,
        http_client=client,
    )

    assert r[0]["count"] == 5


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


def test_load_returns_dataset():
    manifest = Path(__file__).parent / "demo-vocabs" / "manifest-mainEntity.ttl"
    ds = load(manifest, return_data_type=ReturnDatatype.dataset)
    assert isinstance(ds, Dataset)
    assert len(ds) == 175


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
# def test_load_cli_sparql(sparql_endpoint):
#     warnings.filterwarnings(
#         "ignore", category=DeprecationWarning
#     )  # ignore RDFLib's ConjunctiveGraph warning
#
#     manifest = Path(__file__).parent / "demo-vocabs/manifest.ttl"
#     response = runner.invoke(
#         app,
#         [
#             "load",
#             "sparql",
#             manifest,
#             sparql_endpoint,
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
#     r = query(
#         sparql_endpoint,
#         q,
#         return_format="python",
#         return_bindings_only=True,
#         http_client=client,
#     )
#
#     count = int(r[0]["count"])
#
#     assert count == 5

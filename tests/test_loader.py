from prezmanifest import load
from pathlib import Path
from rdflib import Dataset, URIRef
import warnings
from kurrawong.fuseki import query, upload


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

    r = query(
        SPARQL_ENDPOINT, q, return_python=True, return_bindings_only=True
    )

    count = int(r[0]["count"]["value"])

    assert count == 2

    q = "DROP GRAPH <XXX>".replace("XXX", TESTING_GRAPH)

    print("QUERY")
    print(q)
    print("QUERY")

    r = query(SPARQL_ENDPOINT, q)

    print(r)


def test_load_to_quads_file():
    warnings.filterwarnings("ignore", category=DeprecationWarning)  # ignore RDFLib's ConjunctiveGraph warning
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



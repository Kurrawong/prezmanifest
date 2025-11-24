import io
from pathlib import Path

import httpx
from git import Repo
from rdflib import RDF, SDO, BNode, Dataset, Graph, Literal, URIRef
from rdflib.compare import to_canonical_graph
from rdflib.query import Result

from prezmanifest import load
from prezmanifest.definednamespaces import MVT, OLIS
from prezmanifest.event.client import EventClient
from prezmanifest.loader import ReturnDatatype


def _add_commit_hash_to_dataset(commit_hash: str, ds: Dataset) -> Dataset:
    """Load a manifest, add the commit hash to the system graph, and return the dataset.

    Parameters:
        commit_hash: The commit hash to add to the system graph.
        ds: A manifest dataset.

    Raises:
        ValueError: If the Olis system graph does not contain a Virtual Graph.

    Returns:
        The modified dataset.
    """
    graph = ds.graph(OLIS.SystemGraph)
    vg_iri = graph.value(predicate=RDF.type, object=OLIS.VirtualGraph)
    if vg_iri is None:
        raise ValueError(
            "Could not find the Virtual Graph instance in the Olis system graph"
        )
    version_object = BNode()
    graph.add((vg_iri, SDO.version, version_object))
    graph.add((version_object, SDO.additionalType, MVT.GitCommitHash))
    graph.add((version_object, SDO.value, Literal(commit_hash)))
    return ds


def _retrieve_commit_hash(
    vg_iri: URIRef, sparql_endpoint: str, http_client: httpx.Client
) -> str | None:
    """Retrieve the current commit hash from the SPARQL endpoint's Olis system graph.

    Parameters:
        sparql_endpoint: The URL of the SPARQL Endpoint.
        http_client: The HTTP client to use for making requests.

    Returns:
        The git commit hash `str` or `None`.

            None would indicate at least one of the following is missing:
             - The Olis system graph
             - The virtual graph instance
             - The git commit hash

            In any of the cases above, it would require loading the entire manifest content with an append-only
            RDF patch log.
    """
    query = f"""
        PREFIX mvt: <https://prez.dev/ManifestVersionTypes/>
        PREFIX olis: <https://olis.dev/>
        PREFIX schema: <https://schema.org/>
        CONSTRUCT {{
            <{vg_iri}> schema:version ?commit_hash
        }}
        WHERE {{
            GRAPH olis:SystemGraph {{
                <{vg_iri}> schema:version [
                    schema:additionalType mvt:GitCommitHash ;
                    schema:value ?commit_hash    
                ]
            }}
        }}
    """
    headers = {
        "Content-Type": "application/sparql-query",
        "Accept": "application/n-triples",
    }
    response = http_client.post(sparql_endpoint, headers=headers, content=query)
    response.raise_for_status()
    result = Result.parse(
        io.BytesIO(response.content),
        content_type=response.headers["Content-Type"].split(";")[0],
    )
    return result.graph.value(subject=vg_iri, predicate=SDO.version)


def _rdf_patch_body_substr(s: str) -> str:
    """Extract the RDF patch body from a string."""
    tx = "TX ."
    tc = "TC ."
    tx_pos = s.find(tx)
    tc_pos = s.find(tc) + len(tc)
    return s[tx_pos:tc_pos]


def _generate_canon_dataset(ds: Dataset) -> Dataset:
    """Generate a canonical dataset from a dataset."""
    return_ds = Dataset()
    for graph in ds.graphs():
        canon_graph = to_canonical_graph(graph)
        target_graph = return_ds.graph(graph.identifier)
        for triple in canon_graph:
            target_graph.add(triple)
    return return_ds


def _generate_rdf_patch_body_add(ds: Dataset) -> str:
    """Generate an add-only RDF patch body from a dataset."""
    return_ds = _generate_canon_dataset(ds)
    output = return_ds.serialize(format="patch", operation="add")
    return _rdf_patch_body_substr(output)


def _generate_rdf_patch_body_diff(ds: Dataset, previous_ds: Dataset) -> str:
    """Generate an RDF patch body diff between two datasets."""
    previous_ds = _generate_canon_dataset(previous_ds)
    ds = _generate_canon_dataset(ds)
    output = previous_ds.serialize(format="patch", target=ds)
    return _rdf_patch_body_substr(output)


def sync_rdf_delta(
    current_working_directory: Path,
    manifest: Path | tuple[Path, Path, Graph],
    sparql_endpoint: str,
    http_client: httpx.Client,
    event_client: EventClient,
):
    """Synchronize a Prez Manifest's resources with an event-based system that takes RDF patches.

    Parameters:
        current_working_directory: The current working directory path.
        manifest: The path of the Prez Manifest file to be loaded.
        sparql_endpoint: The URL of the SPARQL Endpoint.
        http_client: The HTTP client to use for making requests.
        event_client: The event client to use for sending events.
    """

    # Load the manifest on the latest commit.
    ds = load(manifest, return_data_type=ReturnDatatype.dataset)
    system_graph = ds.graph(OLIS.SystemGraph)
    vg_iri = system_graph.value(predicate=RDF.type, object=OLIS.VirtualGraph)
    if vg_iri is None:
        raise ValueError(
            "Could not find the Virtual Graph instance in the Olis system graph"
        )

    # Query the SPARQL endpoint and retrieve the git commit hash version from the system graph.
    previous_commit_hash = _retrieve_commit_hash(vg_iri, sparql_endpoint, http_client)

    # The current commit hash. Assume this is the latest.
    repo = Repo(current_working_directory)
    current_commit_hash = repo.head.commit.hexsha

    if previous_commit_hash is None:
        _add_commit_hash_to_dataset(current_commit_hash, ds)
        rdf_patch_body = _generate_rdf_patch_body_add(ds)
    else:
        # Check out the previous commit.
        # Generate the previous manifest dataset.
        repo.git.checkout(previous_commit_hash)
        previous_ds = load(manifest, return_data_type=ReturnDatatype.dataset)
        _add_commit_hash_to_dataset(previous_commit_hash, previous_ds)
        _add_commit_hash_to_dataset(current_commit_hash, ds)

        # Generate an RDF patch between the previous commit dataset and the current commit dataset.
        rdf_patch_body = _generate_rdf_patch_body_diff(ds, previous_ds)

    # Create the event.
    event_client.create_event(rdf_patch_body)

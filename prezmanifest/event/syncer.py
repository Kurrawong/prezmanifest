import io
import logging
from pathlib import Path
from typing import Generator

import httpx
from git import Repo
from rdflib import RDF, SDO, BNode, Dataset, Graph, Literal, URIRef
from rdflib.compare import to_canonical_graph
from rdflib.query import Result

from prezmanifest import load
from prezmanifest.definednamespaces import MVT, OLIS
from prezmanifest.event.client import EventClient
from prezmanifest.loader import ReturnDatatype

logger = logging.getLogger(__name__)


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


def _rdf_patch_body_substr(s: str) -> Generator[str, None, None]:
    """Extract the RDF patch body from a string and yield chunks of ~0.8 MB.

    Chunks the patch body into approximately 0.8 MB pieces to fit within
    event streaming platform message size limits (typically 1 MB, with 0.2 MB
    reserved for metadata).

    Yields:
        Chunks of the RDF patch body, attempting to break on line boundaries
        when possible to avoid splitting individual patch statements.
    """
    tx = "TX ."
    tc = "TC ."
    tx_pos = s.find(tx)
    tc_pos = s.find(tc) + len(tc)
    body = s[tx_pos:tc_pos]

    # Chunk size: 0.8 MB in bytes (0.8 * 1024 * 1024)
    chunk_size = 838860

    start = 0
    while start < len(body):
        end = min(start + chunk_size, len(body))
        if end < len(body):
            # Try to break on a newline to avoid splitting lines
            newline_pos = body.rfind("\n", start, end)
            if newline_pos > start:
                end = newline_pos + 1
        yield body[start:end]
        start = end


def _generate_canon_dataset(ds: Dataset) -> Dataset:
    """Generate a canonical dataset from a dataset."""
    return_ds = Dataset()
    for graph in ds.graphs():
        canon_graph = to_canonical_graph(graph)
        target_graph = return_ds.graph(graph.identifier)
        for triple in canon_graph:
            target_graph.add(triple)
    return return_ds


def _generate_rdf_patch_from_datasets(ds: Dataset, previous_ds: Dataset) -> str:
    """Generate an RDF patch body from two datasets.

    Computes the diff between datasets and generates an RDF patch
    with TX/TC markers but no header.

    Parameters:
        ds: The current/target dataset.
        previous_ds: The previous/source dataset.

    Returns:
        RDF patch body string with TX . at start and TC . at end.
    """
    # Convert datasets to sets of quads for faster diff operations
    logger.info("Extracting quads from current dataset")
    ds_quads = set(ds.quads())
    logger.info(f"Quads: {len(ds_quads)}")
    logger.info("Extracting quads from previous dataset")
    previous_ds_quads = set(previous_ds.quads())
    logger.info(f"Quads: {len(previous_ds_quads)}")

    # Compute diffs using set operations
    # Statements in previous but not in current = deletions
    logger.info("Computing deletions (previous - current)")
    to_delete_quads = previous_ds_quads - ds_quads
    # Statements in current but not in previous = additions
    logger.info("Computing additions (current - previous)")
    to_add_quads = ds_quads - previous_ds_quads

    # Build patch body
    lines = ["TX ."]

    # Serialize and add deletion statements
    logger.info("Serializing deletions to N-Quads")
    if to_delete_quads:
        delete_ds = Dataset()
        for s, p, o, g in to_delete_quads:
            delete_ds.add((s, p, o, g))
        delete_nquads = delete_ds.serialize(format="nquads")
        for line in delete_nquads.strip().split("\n"):
            if line:
                lines.append(f"D {line}")

    # Serialize and add addition statements
    logger.info("Serializing additions to N-Quads")
    if to_add_quads:
        add_ds = Dataset()
        for s, p, o, g in to_add_quads:
            add_ds.add((s, p, o, g))
        add_nquads = add_ds.serialize(format="nquads")
        for line in add_nquads.strip().split("\n"):
            if line:
                lines.append(f"A {line}")

    lines.append("TC .")

    logger.info("RDF patch generation done")
    return "\n".join(lines)


def _generate_rdf_patch_body_add(ds: Dataset) -> Generator[str, None, None]:
    """Generate an add-only RDF patch body from a dataset.

    Yields:
        Chunks of the RDF patch body.
    """
    logger.info("Canonicalising add-only dataset")
    return_ds = _generate_canon_dataset(ds)
    logger.info("Serializing add-only RDF patch body to string")
    output = return_ds.serialize(format="patch", operation="add")
    logger.info("Serialization done.")
    yield from _rdf_patch_body_substr(output)


def _generate_rdf_patch_body_diff(
    ds: Dataset, previous_ds: Dataset
) -> Generator[str, None, None]:
    """Generate an RDF patch body diff between two datasets.

    Yields:
        Chunks of the RDF patch body.
    """
    logger.info("Canonicalising diff-only previous dataset")
    previous_ds = _generate_canon_dataset(previous_ds)
    logger.info("Canonicalising diff-only current dataset")
    ds = _generate_canon_dataset(ds)
    logger.info("Serializing diff-only RDF patch body to string")
    output = _generate_rdf_patch_from_datasets(ds, previous_ds)
    logger.info("Serialization done.")
    yield from _rdf_patch_body_substr(output)


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
    logger.info(f"Virtual Graph IRI: {vg_iri}")

    # Query the SPARQL endpoint and retrieve the git commit hash version from the system graph.
    previous_commit_hash = _retrieve_commit_hash(vg_iri, sparql_endpoint, http_client)
    logger.info(f"Previous commit hash: {previous_commit_hash}")

    # The current commit hash. Assume this is the latest.
    repo = Repo(current_working_directory)
    current_commit_hash = repo.head.commit.hexsha
    logger.info(f"Current commit hash: {current_commit_hash}")

    if previous_commit_hash is None:
        logger.info(
            "Previous commit hash is None. Adding current commit hash to dataset."
        )
        logger.info("Adding commit hash to current manifest dataset")
        _add_commit_hash_to_dataset(current_commit_hash, ds)
        logger.info("Generating RDF patch body chunks for add operation")
        rdf_patch_body_chunks = _generate_rdf_patch_body_add(ds)
    else:
        # Check out the previous commit.
        # Generate the previous manifest dataset.
        logger.info(f"Checking out previous commit: {previous_commit_hash}")
        repo.git.checkout(previous_commit_hash)
        logger.info("Loading previous manifest dataset")
        previous_ds = load(manifest, return_data_type=ReturnDatatype.dataset)
        logger.info("Adding commit hash to previous manifest dataset")
        _add_commit_hash_to_dataset(previous_commit_hash, previous_ds)
        logger.info("Adding commit hash to current manifest dataset")
        _add_commit_hash_to_dataset(current_commit_hash, ds)

        # Generate an RDF patch between the previous commit dataset and the current commit dataset.
        logger.info("Generating RDF patch body chunks for diff operation")
        rdf_patch_body_chunks = _generate_rdf_patch_body_diff(ds, previous_ds)

    # Create events for each chunk.
    for i, chunk in enumerate(rdf_patch_body_chunks):
        logger.info(f"Creating event for chunk {i + 1}")
        event_client.create_event(chunk)

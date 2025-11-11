import io
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

import httpx
from git import Repo
from kurra.db import clear_graph, sparql, upload
from kurra.sparql import query
from kurra.utils import load_graph
from rdf_delta import DeltaClient
from rdflib import BNode, Dataset, Graph, Literal, URIRef
from rdflib.namespace import RDF, SDO
from rdflib.query import Result

from prezmanifest.definednamespaces import MRR, MVT, OLIS
from prezmanifest.loader import ReturnDatatype, load
from prezmanifest.utils import (
    VersionIndicatorComparison,
    absolutise_path,
    denormalise_artifacts,
    get_manifest_paths_and_graph,
    store_remote_artifact_locally,
    update_local_artifact,
    which_is_more_recent,
)


def sync(
    manifest: Path | tuple[Path, Path, Graph],
    sparql_endpoint: str = None,
    http_client: httpx.Client = httpx.Client(),
    update_remote: bool = True,
    update_local: bool = True,
    add_remote: bool = True,
    add_local: bool = True,
) -> dict:
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )

    sync_status = {}
    # For each Artifact in the Manifest
    artifacts = denormalise_artifacts((manifest_path, manifest_root, manifest_graph))
    local_entities = [v["main_entity"] for k, v in artifacts.items()]

    cat_iri = None
    cat_artifact_path = None
    for k, v in artifacts.items():
        if v["role"] in [MRR.ResourceData, MRR.CatalogueData]:
            # save cat_iri for later
            if v["role"] in MRR.CatalogueData:
                cat_iri = v["main_entity"]
                cat_artifact_path = absolutise_path(k, manifest_root)

            # See if each is known remotely (via Main Entity Graph IRI)
            known = query(
                sparql_endpoint,
                "ASK {GRAPH <xxx> {?s ?p ?o}}".replace("xxx", str(v["main_entity"])),
                http_client,
                return_python=True,
                return_bindings_only=True,
            )
            # If not known by graph IRI, just check if it's the catalogue (+ "-catalogue" to IRI)
            if not known and v["role"] == MRR.CatalogueData:
                known = query(
                    sparql_endpoint,
                    "ASK {GRAPH <xxx> {?s ?p ?o}}".replace(
                        "xxx", str(v["main_entity"] + "-catalogue")
                    ),
                    http_client,
                    return_python=True,
                    return_bindings_only=True,
                )

            # If known, compare it
            if known:
                replace = which_is_more_recent(
                    v,
                    sparql_endpoint,
                    http_client,
                )
                if replace == VersionIndicatorComparison.First:
                    direction = "upload"
                elif replace == VersionIndicatorComparison.Second:
                    direction = "download"
                elif replace == VersionIndicatorComparison.Neither:
                    direction = "same"
                elif VersionIndicatorComparison.CantCalculate:
                    direction = "upload"
            else:  # not known at remote location so forward sync - upload
                direction = "add-remotely"

            sync_status[str(k)] = {
                "main_entity": v["main_entity"],
                "direction": direction,
                "sync": v["sync"],
            }

    # Check for things at remote not known in local
    q = """
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX schema: <https://schema.org/>
    
        SELECT ?p
        WHERE {
            GRAPH ?g {
                <xxx> schema:hasPart|dcterms:hasPart ?p
            }
        }
        """.replace("xxx", str(cat_iri))
    for x in query(
        sparql_endpoint, q, http_client, return_python=True, return_bindings_only=True
    ):
        remote_entity = URIRef(x["p"]["value"])
        if remote_entity not in local_entities:
            sync_status[str(remote_entity)] = {
                "main_entity": URIRef(remote_entity),
                "direction": "add-locally",
                "sync": True,
            }

    update_remote_catalogue = False
    for k, v in sync_status.items():
        if v["sync"]:
            if update_remote and v["direction"] == "upload":
                clear_graph(sparql_endpoint, v["main_entity"], http_client)
                upload(sparql_endpoint, Path(k), v["main_entity"], False, http_client)

            if add_remote and v["direction"] == "add-remotely":
                # no need to clear_graph() as this asset doesn't exist remotely
                upload(sparql_endpoint, Path(k), v["main_entity"], False, http_client)
                update_remote_catalogue = True

            if add_local and v["direction"] == "add-locally":
                updated_local_manifest = store_remote_artifact_locally(
                    (manifest_path, manifest_root, manifest_graph),
                    sparql_endpoint,
                    v["main_entity"],
                    http_client,
                )

                updated_local_manifest.bind(
                    "mrr", "https://prez.dev/ManifestResourceRoles"
                )
                updated_local_manifest.serialize(
                    destination=manifest_path, format="longturtle"
                )
                cat = load_graph(cat_artifact_path)
                cat.add((cat_iri, SDO.hasPart, URIRef(v["main_entity"])))
                cat.serialize(destination=cat_artifact_path, format="longturtle")

            if update_local and v["direction"] == "download":
                update_local_artifact(
                    (manifest_path, manifest_root, manifest_graph),
                    Path(k),
                    sparql_endpoint,
                    v["main_entity"],
                    http_client,
                )

    if update_remote_catalogue:
        # TODO: work out why SILENT is needed. Why isn't the cat_iri graph known? Should have been uploaded by sync already
        sparql(sparql_endpoint, f"DROP SILENT GRAPH <{cat_iri}>")
        upload(
            sparql_endpoint,
            cat_artifact_path,
            cat_iri,
            False,
            http_client,
        )

    return sync_status


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


def _generate_rdf_patch_body_add(ds: Dataset) -> str:
    """Generate an add-only RDF patch body from a dataset."""
    output = ds.serialize(format="patch", operation="add")
    return _rdf_patch_body_substr(output)


def _generate_rdf_patch_body_diff(ds: Dataset, previous_ds: Dataset) -> str:
    """Generate an RDF patch body diff between two datasets."""
    output = previous_ds.serialize(format="patch", target=ds)
    return _rdf_patch_body_substr(output)


class EventClient(Protocol):
    def create_event(self, payload: str) -> None: ...


class DeltaEventClient:
    def __init__(self, url: str, datasource: str) -> None:
        self._inner = DeltaClient(url)
        self.datasource = datasource

    def _add_patch_log_header(self, patch_log: str) -> str:
        ds = self._inner.describe_datasource(self.datasource)
        ds_log = self._inner.describe_log(ds.id)
        previous_id = ds_log.latest
        new_id = str(uuid4())
        if previous_id:
            modified_patch_log = (
                f"""
                    H id <uuid:{new_id}> .
                    H prev <uuid:{previous_id}> .
                """
                + patch_log
            )
        else:
            modified_patch_log = (
                f"""
                H id <uuid:{new_id}> .
            """
                + patch_log
            )
        return modified_patch_log

    def create_event(self, payload: str) -> None:
        patch_log = self._add_patch_log_header(payload)
        self._inner.create_log(patch_log, self.datasource)


def sync_rdf_delta(
    current_working_directory: Path,
    manifest: Path | tuple[Path, Path, Graph],
    sparql_endpoint: str,
    http_client: httpx.Client,
    event_client: EventClient,
) -> dict[Any, Any]:
    """Synchronize a Prez Manifest's resources with an event-based system that takes RDF patches.

    Parameters:
        current_working_directory: The current working directory path.
        manifest: The path of the Prez Manifest file to be loaded.
        sparql_endpoint: The URL of the SPARQL Endpoint.
        http_client: The HTTP client to use for making requests.
        event_client: The event client to use for sending events.

    Returns:
        Sync status dict where the key is the entity name and the value is a status dict with the following keys:
        - main_entity
        - direction
        - sync
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

        # Generate an RDF patch between the previous commit dataset and the current commit dataset.
        rdf_patch_body = _generate_rdf_patch_body_diff(ds, previous_ds)

    # Create the event.
    event_client.create_event(rdf_patch_body)

    # Return the status dict
    return {}

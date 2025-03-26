from pathlib import Path

import httpx
from kurra.db import upload, clear_graph
from kurra.sparql import query
from kurra.utils import load_graph
from rdflib import Graph
from rdflib import URIRef
from rdflib.namespace import SDO

from prezmanifest.definednamespaces import MRR
from prezmanifest.utils import (
    VersionIndicatorComparison,
    store_remote_artifact_locally,
    update_local_artifact,
    absolutise_path,
)
from prezmanifest.utils import (
    get_manifest_paths_and_graph,
    denormalise_artifacts,
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
        """.replace(
        "xxx", str(cat_iri)
    )
    for x in query(
        sparql_endpoint, q, http_client, return_python=True, return_bindings_only=True
    ):
        remote_entity = URIRef(x["p"]["value"])
        if remote_entity not in local_entities:
            sync_status[str(remote_entity)] = {
                "main_entity": URIRef(remote_entity),
                "direction": "add-locally",
            }

    update_remote_catalogue = False
    for k, v in sync_status.items():
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

            updated_local_manifest.bind("mrr", "https://prez.dev/ManifestResourceRoles")
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
        clear_graph(sparql_endpoint, cat_iri, http_client)
        upload(
            sparql_endpoint,
            cat_artifact_path,
            cat_iri,
            False,
            http_client,
        )

    return sync_status

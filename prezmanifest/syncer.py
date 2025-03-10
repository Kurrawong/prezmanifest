from pathlib import Path

import httpx
from rdflib import Graph

from prezmanifest.definednamespaces import MRR
from prezmanifest.utils import get_manifest_paths_and_graph, denormalise_artifacts, local_artifact_more_recent
from kurra.sparql import query
from kurra.db import upload
from prezmanifest.utils import ArtifactComparison, store_remote_artifact_locally, update_local_artifact
from rdflib import URIRef

def sync(
    manifest: Path | tuple[Path, Path, Graph],
    sparql_endpoint: str = None,
    http_client: httpx.Client | None = None,
    update_remote: bool = True,
    update_local: bool = True,
    add_remote: bool = True,
    add_local: bool = True,
) -> None:
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(manifest)

    sync_status = {}

    # For each Artifact in the Manifest
    artifacts = denormalise_artifacts((manifest_path, manifest_root, manifest_graph))
    local_entities = [v["main_entity"] for k, v in artifacts.items()]

    cat_iri = None
    for k, v in artifacts.items():
        if v["role"] in [MRR.ResourceData, MRR.CatalogueData]:
            # save cat_iri for later
            if v["role"] in MRR.CatalogueData:
                cat_iri = v["main_entity"]

            # See if each is known remotely (via Main Entity Graph IRI)
            known = query(
                sparql_endpoint,
                "ASK {GRAPH <xxx> {?s ?p ?o}}".replace("xxx", str(v["main_entity"])),
                http_client,
                return_python=True,
                return_bindings_only=True
            )
            # If not known by graph IRI, just check if it's the catalogue (+ "-catalogue" to IRI)
            if not known and v["role"] == MRR.CatalogueData:
                known = query(
                    sparql_endpoint,
                    "ASK {GRAPH <xxx> {?s ?p ?o}}".replace("xxx", str(v["main_entity"] + "-catalogue")),
                    http_client,
                    return_python=True,
                    return_bindings_only=True
                )

            # If known, compare it
            if known:
                replace = local_artifact_more_recent(
                    v,
                    sparql_endpoint,
                    http_client,
                )
                if replace == ArtifactComparison.First:
                    direction = "forward"
                elif replace == ArtifactComparison.Second:
                    direction = "reverse"
                elif replace == ArtifactComparison.Neither:
                    direction = "unchanged"
                elif ArtifactComparison.CantCalculate:
                    direction = "forward"
            else:  # not known at remote location so forward sync - upload
                direction = "missing-remotely"

            sync_status[k] = {
                "main_entity": v["main_entity"],
                "direction": direction
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
    for x in query(sparql_endpoint, q, http_client, return_python=True, return_bindings_only=True):
        remote_entity = URIRef(x["p"]["value"])
        if remote_entity not in local_entities:
            sync_status[URIRef(remote_entity)] = {
                "main_entity": URIRef(remote_entity),
                "direction": "missing-locally"
            }

    for k, v in sync_status.items():
        print(k, v)

    for k, v in sync_status.items():
        if update_remote and v["direction"] == "forward":
            upload(sparql_endpoint, k, v["main_entity"], False, http_client)
            print(f"updated {k} to remote")

        if add_remote and v["direction"] == "missing-remotely":
            upload(sparql_endpoint, k, v["main_entity"], False, http_client)
            print(f"added {k} to remote")
            # TODO: ensure remote catalogue is updated

        if add_local and v["direction"] == "missing-locally":
            x = store_remote_artifact_locally(
                (manifest_path, manifest_root, manifest_graph),
                sparql_endpoint,
                v["main_entity"],
                http_client,
            )
            print(f"addedd {k} locally")

        if update_local and v["direction"] == "reverse":
            update_local_artifact(
                (manifest_path, manifest_root, manifest_graph),
                k,
                sparql_endpoint,
                v["main_entity"],
                http_client,
            )
            print(f"updated {k} locally")

    print("sync complete")
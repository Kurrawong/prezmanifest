from pathlib import Path

import httpx
from rdflib import Graph

from prezmanifest.definednamespaces import MRR
from prezmanifest.utils import get_manifest_paths_and_graph, denormalise_artifacts, \
    local_artifact_is_more_recent_then_stored_data


def sync(
    manifest: Path | tuple[Path, Path, Graph],
    sparql_endpoint: str = None,
    http_client: httpx.Client | None = None,
) -> None:
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(manifest)

    # List each artifact in the local Manifest
    #   with all their details filled in - Main Entities & Version Indicators
    artifacts = denormalise_artifacts((manifest_path, manifest_root, manifest_graph))

    for x in artifacts:
        print()
        print(x)
    exit()

    print()
    for artifact in artifacts:
        role = artifact[6]
        if role in [MRR.ResourceData, MRR.CatalogueData]:
            local_newer = local_artifact_is_more_recent_then_stored_data(
                (manifest_path, manifest_root, manifest_graph),
                artifact[0],
                sparql_endpoint,
                http_client,
            )
        else:
            local_newer = False

        print(artifact[0], local_newer)
        # print(artifact)
        print()

    return None

    # Try and find each artifact in the remote location
    #   look for the catalogue and list its parts
    #   look for each Named/Virtual Graph with that IRI
    #   fill in all their details via queries


    # get the IRI of the catalogue


    # check and update
    # ask the destination if it knows about that IRI - must be a Virtual Graph or a Real Graph



    # does the target have a VG for this manifest?
    # if no
    #   raise error

    # inspect the source to see if it's Git
    # if yes
    #   inspect the target to see if it contains Git info
    #   get Git info per resource
    # if no
    #   try file system info
    #   if yes
    #       inspect target for file system info
    #   if no
    #       inspect resources for content versioning info

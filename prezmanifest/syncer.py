from pathlib import Path

from rdflib import Graph

from prezmanifest.utils import get_manifest_paths_and_graph, get_catalogue_iri_from_manifest, denormalise_artifacts


def sync(
    manifest: Path | tuple[Path, Path, Graph],
    sparql_endpoint: str = None,
    sparql_username: str = None,
    sparql_password: str = None,
) -> None:
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(manifest)

    # List each artifact in the local Manifest
    #   with all their details filled in - Main Entities & Version Indicators
    artifacts = denormalise_artifacts()

    # Try and find each artifact in the remote location
    #   look for the catalogue and list its parts
    #   look for each Named/Virtual Graph with that IRI
    #   fill in all their details via queries


    # get the IRI of the catalogue


    cat_iri = get_catalogue_iri_from_manifest((manifest_graph, manifest_root))

    # check and update
    # ask the destination if it knows about that IRI - must be a Virtual Graph or a Real Graph

    return cat_iri

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

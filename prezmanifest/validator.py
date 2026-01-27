"""Validate a Prez Manifest file.

This script performs both SHACL validation to ensure the Manifest is valid according to the Prez Manifest
specification (see https://prez.dev/manifest/) and checks that all the resources indicated by the Manifest
- whether local files/folders or remote resources on the Internet - are reachable.

~$ python validate.py {MANIFEST_FILE_PATH}"""

from pathlib import Path

import httpx
import kurra.shacl
from kurra.utils import load_graph
from pyparsing import Literal
from rdflib import BNode, Graph, URIRef
from rdflib.namespace import DCTERMS, PROF, SDO

from prezmanifest.utils import get_background_graph, get_files_from_artifact


class ManifestValidationError(Exception):
    pass


def validate(manifest: Path) -> Graph:
    """Validates a manifest and any assets listed in it with a conformance claim.

    Uses validators known in the Semantic Background or supplied by the user.

    Args:
        manifest: path to a manifest file

    Returns:
        Graph of validated manifest
    """

    # can't use get_manifest_paths_and_graph() here as that function uses validate()
    manifest_path = manifest
    manifest_root = Path(manifest).parent.resolve()
    manifest_graph = load_graph(manifest)

    ME = Path(__file__)

    def literal_resolves_as_file_folder_or_url(lit: Literal):
        l_str = str(lit)
        if l_str.startswith("http") and "://" in l_str:
            r = httpx.get(l_str)
            if 200 <= r.status_code < 400:
                pass
            else:
                raise ManifestValidationError(
                    f"Remote content link non-resolving: {l_str}"
                )
        elif "*" in l_str:
            glob_parts = l_str.split("*")
            dir = Path(manifest_root / Path(glob_parts[0]))
            if not Path(dir).is_dir():
                raise ManifestValidationError(
                    f"The content link {l_str} is not a directory"
                )
        else:
            # It must be a local
            if not (manifest_root / l_str).is_file():
                raise ManifestValidationError(
                    f"Content link {manifest_root / l_str} is invalid - not a file"
                )

    # validate the manifest
    if not kurra.shacl.check_validator_known("https://prez.dev/manifest-validator"):
        kurra.shacl.sync_validators()

    v = kurra.shacl.validate(
        [manifest_graph, load_graph(ME.parent / "mrr.ttl")],
        "https://prez.dev/manifest-validator",
    )
    if not v[0]:
        raise ManifestValidationError(f"The manifest file is invalid:\n\n{v[2]}")

    # get the background graph for merging into artifact graphs for validation
    background_graph = get_background_graph(manifest)

    # validate each resource with a conformance claim
    # check all conformance claims validators indicated by IRI are known
    # if any ar unknown, force a validator sync
    for validator in manifest_graph.objects(subject=None, predicate=DCTERMS.conformsTo):
        if not kurra.shacl.check_validator_known(str(validator)):
            kurra.shacl.sync_validators()

    # recheck all, in case we had a sync
    for validator in manifest_graph.objects(subject=None, predicate=DCTERMS.conformsTo):
        if str(validator).startswith("http"):
            if not kurra.shacl.check_validator_known(str(validator)):
                raise ManifestValidationError(
                    f"The validator <{validator}> indicated in the manifest file is not known to the Semantic Background"
                )

    # validate each file referenced in the Manifest
    for s, resource in manifest_graph.subject_objects(PROF.hasResource):
        for artifact in manifest_graph.objects(resource, PROF.hasArtifact):
            if isinstance(artifact, BNode):
                content_location = manifest_graph.value(
                    subject=artifact, predicate=SDO.contentLocation
                )
                # main_entity = manifest_graph.value(subject=artifact, predicate=SDO.mainEntity)
            else:
                content_location = artifact

            # ensure the artifact resolves
            literal_resolves_as_file_folder_or_url(content_location)

            # validate each file in the artifact
            for file in get_files_from_artifact(
                (manifest_path, manifest_root, manifest_graph), content_location
            ):
                # if there is a conformance claim validator for this artifact, use it
                validator = manifest_graph.value(
                    subject=artifact, predicate=DCTERMS.conformsTo
                )

                # if not, check if the resource has one to use
                if validator is None:
                    validator = manifest_graph.value(
                        subject=resource, predicate=DCTERMS.conformsTo
                    )

                if validator is not None:
                    try:
                        data_graph = load_graph(manifest_root / file)
                    except SyntaxError as e:
                        raise SyntaxError(f"Failed to load {file}: {e}")

                    # all validators indicated in the Manifest will have been confirmed known at this point
                    # or are supplied
                    if isinstance(validator, URIRef):
                        pass
                    else:  # must be a local file
                        validator = manifest_root / str(validator)

                    v = kurra.shacl.validate(
                        [data_graph, background_graph], str(validator)
                    )
                    if not v[0]:
                        raise ManifestValidationError(
                            f"the artifact {manifest_root / file} is invalid according to validator {validator}:\n\n{v[2]}"
                        )

    return manifest_graph

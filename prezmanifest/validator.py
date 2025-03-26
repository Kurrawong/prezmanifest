"""Validate a Prez Manifest file.

This script performs both SHACL validation to ensure the Manifest is valid according to the Prez Manifest
specification (see https://prez.dev/manifest/) and checks that all the resources indicated by the Manifest
- whether local files/folders or remote resources on the Internet - are reachable.

~$ python validate.py {MANIFEST_FILE_PATH}"""

from pathlib import Path

import httpx
from kurra.utils import load_graph
from pyparsing import Literal
from pyshacl import validate as shacl_validate
from rdflib import BNode, Dataset, Graph
from rdflib.namespace import DCTERMS, PROF, SDO

from prezmanifest.definednamespaces import MRR
from prezmanifest.utils import get_files_from_artifact, get_validator_graph


class ManifestValidationError(Exception):
    pass


def validate(manifest: Path) -> Graph:
    # can't use get_manifest_paths_and_graph() here as that function uses validate()
    manifest_path = manifest
    manifest_root = Path(manifest).parent.resolve()
    manifest_graph = load_graph(manifest)

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

    def shacl_validate_resource(data_graph, shacl_graph) -> (bool, str | None):
        valid, v_graph, v_text = shacl_validate(
            data_graph, shacl_graph=shacl_graph, allow_warnings=True
        )
        if valid:
            return True, None
        else:
            return False, v_text

    ME = Path(__file__)

    # SHACL validation

    mrr_vocab_graph = load_graph(ME.parent / "mrr.ttl")
    shacl_graph = load_graph(ME.parent / "validator.ttl")
    valid, error_msg = shacl_validate_resource(
        manifest_graph + mrr_vocab_graph, shacl_graph
    )
    if not valid:
        raise ManifestValidationError(f"Manifest Shapes invalid:\n\n{error_msg}")

    # get labels graph for SHACL validation
    context_graph = Graph()
    for s, o in manifest_graph.subject_objects(PROF.hasResource):
        for role in manifest_graph.objects(o, PROF.hasRole):
            # The data files & background - must be processed after Catalogue
            if role in [
                MRR.CompleteCatalogueAndResourceLabels,
                MRR.IncompleteCatalogueAndResourceLabels,
            ]:
                for artifact in manifest_graph.objects(o, PROF.hasArtifact):
                    for f in get_files_from_artifact(
                        (manifest_path, manifest_root, manifest_graph), artifact
                    ):
                        if not f.is_file():
                            raise ManifestValidationError(f"Artifact {f} is not a file")

                        if str(f.name).endswith(".ttl"):
                            context_graph += load_graph(f)
                        elif str(f.name).endswith(".trig"):  # TODO: test this option
                            d = Dataset()
                            d.parse(f, format="trig")
                            for g in d.graphs:
                                context_graph += g

    # Content link validation
    for s, o in manifest_graph.subject_objects(PROF.hasResource):
        # see if there's a conformance claim for the resource
        cc = manifest_graph.value(subject=o, predicate=DCTERMS.conformsTo)

        for artifact in manifest_graph.objects(o, PROF.hasArtifact):
            if isinstance(artifact, BNode):
                content_location = manifest_graph.value(
                    subject=artifact, predicate=SDO.contentLocation
                )
                # main_entity = manifest_graph.value(subject=artifact, predicate=SDO.mainEntity)
            else:
                content_location = artifact

            # ensure the artifact resolves
            literal_resolves_as_file_folder_or_url(content_location)

            # if we now have a CC for the resource or the artifact, use it
            for file in get_files_from_artifact(
                (manifest_path, manifest_root, manifest_graph), content_location
            ):
                # if there is a conformance claim for this Resource, use it, if not, check if the artifact has one
                if cc is None:
                    cc = manifest_graph.value(
                        subject=artifact, predicate=DCTERMS.conformsTo
                    )
                    artifact_cc = True
                else:
                    artifact_cc = False

                if cc is not None:
                    data_graph = load_graph(manifest_root / file)
                    if context_graph is not None:
                        data_graph += context_graph
                    valid, error_msg = shacl_validate_resource(
                        data_graph,
                        get_validator_graph(
                            (manifest_path, manifest_root, manifest_graph), cc
                        ),
                    )
                    if not valid:
                        raise ManifestValidationError(
                            f"Resource {content_location} Shapes invalid according to conformance claim:\n\n{error_msg}"
                        )

                if artifact_cc:
                    cc = None

    return manifest_graph

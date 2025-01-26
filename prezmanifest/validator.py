"""Validate a Prez Manifest file.

This script performs both SHACL validation to ensure the Manifest is valid according to the Prez Manifest
specification (see https://prez.dev/manifest/) and checks that all the resources indicated by the Manifest
- whether local files/folders or remote resources on the Internet - are reachable.

~$ python validate.py {MANIFEST_FILE_PATH}"""

import argparse
import sys
from pathlib import Path

import httpx
from kurra.utils import load_graph
from pyparsing import Literal
from pyshacl import validate as shacl_validate
from rdflib import Graph, BNode
from rdflib.namespace import DCTERMS, PROF, SDO

try:
    from prezmanifest import MRR, __version__
    from prezmanifest.utils import get_files_from_artifact, get_validator
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).parent.parent.resolve()))
    from prezmanifest import MRR, __version__
    from prezmanifest.utils import get_files_from_artifact, get_validator


def validate(manifest: Path) -> Graph:
    def literal_resolves_as_file_folder_or_url(l: Literal):
        l_str = str(l)
        if "http" in l_str:
            r = httpx.get(l_str)
            if 200 <= r.status_code < 400:
                pass
            else:
                raise ValueError(
                    f"Remote content link non-resolving: {l_str}"
                )
        elif "*" in l_str:
            glob_parts = l_str.split("*")
            dir = Path(manifest.parent / Path(glob_parts[0]))
            if not Path(dir).is_dir():
                raise ValueError(
                    f"The content link {l_str} is not a directory"
                )
        else:
            # It must be a local
            if not (MANIFEST_ROOT_DIR / l_str).is_file():
                raise ValueError(
                    f"Content link {MANIFEST_ROOT_DIR / l_str} is invalid - not a file"
                )

    def shacl_validate_resource(data_graph, shacl_graph) -> (bool, str|None):
        valid, v_graph, v_text = shacl_validate(data_graph, shacl_graph=shacl_graph, allow_warnings=True)
        if valid:
            return True, None
        else:
            return False, v_text

    ME = Path(__file__)
    MANIFEST_ROOT_DIR = manifest.parent

    # SHACL validation
    manifest_graph = load_graph(manifest)
    mrr_vocab_graph = load_graph(ME.parent / "mrr.ttl")
    valid, error = shacl_validate_resource(manifest_graph + mrr_vocab_graph, load_graph(ME.parent / "validator.ttl"))
    if not valid:
        raise ValueError(f"SHACL invalid:\n\n{error}")

    # not yet used
    # # get labels graph for SHACL validation
    # context_graph = Graph()
    # for s, o in manifest_graph.subject_objects(PROF.hasResource):
    #     for role in manifest_graph.objects(o, PROF.hasRole):
    #         # The data files & background - must be processed after Catalogue
    #         if role in [
    #             MRR.CompleteCatalogueAndResourceLabels,
    #             MRR.IncompleteCatalogueAndResourceLabels,
    #         ]:
    #             for artifact in manifest_graph.objects(o, PROF.hasArtifact):
    #                 for f in get_files_from_artifact(manifest_graph, manifest, artifact):
    #                     if str(f.name).endswith(".ttl"):
    #                         context_graph += load_graph(f)

    # Content link validation
    for s, o in manifest_graph.subject_objects(PROF.hasResource):
        for artifact in manifest_graph.objects(o, PROF.hasArtifact):
            if isinstance(artifact, BNode):
                content_location = manifest_graph.value(subject=artifact, predicate=SDO.contentLocation)
                # main_entity = manifest_graph.value(subject=artifact, predicate=SDO.mainEntity)
            else:
                content_location = artifact

            literal_resolves_as_file_folder_or_url(content_location)

            # see if there's a conformance claim for the resource
            cc = manifest_graph.value(subject=artifact, predicate=DCTERMS.conformsTo)
            if cc is not None:
                # not yet used
                # data_graph = load_graph(MANIFEST_ROOT_DIR / content_location) + context_graph
                valid, error = shacl_validate_resource(load_graph(MANIFEST_ROOT_DIR / content_location), get_validator(manifest, cc))
                if not valid:
                    raise ValueError(f"Resource {content_location} invalid according to conformance claim:\n\n{error}")

    return manifest_graph


def setup_cli_parser(args=None):

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="{version}".format(version=__version__),
    )

    parser.add_argument(
        "manifest",
        help="A Manifest file to process",
        type=Path,
    )

    return parser.parse_args(args)


def cli(args=None):
    if args is None:
        args = sys.argv[1:]

    args = setup_cli_parser(args)

    validate(args.manifest)


if __name__ == "__main__":
    retval = cli(sys.argv[1:])
    if retval is not None:
        sys.exit(retval)

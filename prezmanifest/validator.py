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
from pyshacl import validate as shacl_validate
from rdflib import Graph
from rdflib.namespace import PROF

try:
    from prezmanifest import __version__
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).parent.parent.resolve()))
    from prezmanifest import __version__


def validate(manifest: Path) -> bool:
    ME = Path(__file__)
    MANIFEST_ROOT_DIR = manifest.parent

    # SHACL validation
    manifest_graph = load_graph(manifest)
    mrr_vocab_graph = load_graph(ME.parent / "mrr.ttl")
    data_graph = manifest_graph + mrr_vocab_graph
    shacl_graph = load_graph(ME.parent / "validator.ttl")
    valid, v_graph, v_text = shacl_validate(data_graph, shacl_graph=shacl_graph)

    if not valid:
        raise ValueError(f"SHACL invalid:\n\n{v_text}")

    # Content link validation
    for s, o in manifest_graph.subject_objects(PROF.hasResource):
        for artifact in manifest_graph.objects(o, PROF.hasArtifact):
            artifact_str = str(artifact)
            if "http" in artifact_str:
                r = httpx.get(artifact_str)
                if 200 <= r.status_code < 400:
                    pass
                else:
                    raise ValueError(
                        f"Remote content link non-resolving: {artifact_str}"
                    )
            elif "*" in artifact_str:
                glob_parts = artifact_str.split("*")
                dir = Path(manifest.parent / Path(glob_parts[0]))
                if not Path(dir).is_dir():
                    raise ValueError(
                        f"The content link {artifact_str} is not a directory"
                    )
            else:
                # It must be a local
                if not (MANIFEST_ROOT_DIR / artifact_str).is_file():
                    print(
                        f"Content link {MANIFEST_ROOT_DIR / artifact_str} is invalid - not a file"
                    )

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


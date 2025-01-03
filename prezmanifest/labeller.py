"""
Assesses a given Manifest, finds any IRIs in any of the given resources missing labels and tries to patch them from
a given source of labels, such as KurrawongAI's Semantic Background (https://github.com/kurrawong/semantic-background)
repository.
"""
import argparse
import sys
from pathlib import Path
from typing import Literal as TLiteral
from urllib.parse import ParseResult, urlparse

from kurra.utils import load_graph
from labelify import find_missing_labels, extract_labels
from rdflib import Graph, BNode, Literal
from rdflib.namespace import PROF, RDF

from prezmanifest.utils import get_files_from_artifact

try:
    from prezmanifest import MRR, OLIS, validate, load, __version__
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).parent.parent.resolve()))
    from prezmanifest import MRR, OLIS, validate, __version__


def label(
    manifest: Path,
    output: TLiteral["iris", "rdf", "manifest"] = "manifest",
    additional_context: Path | str | Graph = None,
) -> set | Graph | None:
    """"Main function for labeller module"""
    # create the target from the Manifest
    manifest_content_graph = load(manifest, return_data_type="Graph")

    output_types = ["iris", "rdf", "manifest"]
    if output not in output_types:
        raise ValueError(f"Parameter output is {output} but must be one of {', '.join(output_types)}")

    # determine if any labelling context is given in Manifest
    context_graph = Graph()
    for s, o in manifest_content_graph.subject_objects(PROF.hasResource):
        for role in manifest_content_graph.objects(o, PROF.hasRole):
            if role in [
                MRR.IncompleteCatalogueAndResourceLabels,
                MRR.CompleteCatalogueAndResourceLabels,
            ]:
                for artifact in manifest_content_graph.objects(o, PROF.hasArtifact):
                    artifact: Literal
                    for f in get_files_from_artifact(manifest, artifact):
                        context_graph += load_graph(f)

    if output == "iris":
        return find_missing_labels(manifest_content_graph + context_graph, additional_context)

    elif output == "rdf":
        iris = find_missing_labels(manifest_content_graph, context_graph)

        if additional_context is not None:
            return extract_labels(iris, additional_context)
        else:
            return None

    else:  # output == manifest
        # If this is selected, generate the "rdf" output and create a resource for it in the Manifest
        # If there are no more missing labels then we have an mrr:CompleteCatalogueAndResourceLabels
        # else add mrr:IncompleteCatalogueAndResourceLabels

        # Generate labels for any IRIs missing them, using context given in the Manifest and any
        # Additional Context supplied
        manifest_only_graph = load_graph(manifest)
        rdf_addition = label(manifest, "rdf", additional_context)

        if len(rdf_addition) > 0:
            new_artifact = manifest.parent / "labels-additional.ttl"
            rdf_addition.serialize(destination=new_artifact, format="longturtle")
            new_resource = BNode()

            # Find the role of any context in the Manifest
            manifest_iri = None
            context_roles = []
            for s, o in manifest_only_graph.subject_objects(PROF.hasResource):
                manifest_iri = s
                for role in manifest_only_graph.objects(o, PROF.hasRole):
                    if role in [
                        MRR.IncompleteCatalogueAndResourceLabels,
                        MRR.CompleteCatalogueAndResourceLabels,
                    ]:
                        context_roles.append(role)

            if MRR.CompleteCatalogueAndResourceLabels in context_roles and len(context_roles) == 1:
                # If a CompleteCatalogueAndResourceLabels is present in Manifest and yet more labels were discovered,
                # change CompleteCatalogueAndResourceLabels to IncompleteCatalogueAndResourceLabels and add another
                for s, o in manifest_content_graph.subject_objects(PROF.hasRole):
                    if o == MRR.CompleteCatalogueAndResourceLabels:
                        manifest_only_graph.remove((s, PROF.hasRole, o))
                        manifest_only_graph.add((manifest_iri, PROF.hasResource, new_resource))
                        manifest_only_graph.add((new_resource, PROF.hasRole, MRR.IncompleteCatalogueAndResourceLabels))
                        manifest_only_graph.add((new_resource, PROF.hasArtifact, Literal(new_artifact.name)))
            else:
                # If an IncompleteCatalogueAndResourceLabels was present, add another IncompleteCatalogueAndResourceLabels
                # which together make a CompleteCatalogueAndResourceLabels

                # If none was present, add an IncompleteCatalogueAndResourceLabels or a CompleteCatalogueAndResourceLabels
                # TODO: test for completeness of labelling and add in CompleteCatalogueAndResourceLabels if complete
                manifest_only_graph.add((manifest_iri, PROF.hasResource, new_resource))
                manifest_only_graph.add((new_resource, PROF.hasRole, MRR.IncompleteCatalogueAndResourceLabels))
                manifest_only_graph.add((new_resource, PROF.hasArtifact, Literal(new_artifact.name)))

            manifest_only_graph.serialize(destination=manifest, format="longturtle")

        else:
            raise Warning("No new labels have been generated for content in this Manifest. "
                          "This could be because none were missing or because no new labels can be found in any "
                          "supplied additional context.")


def setup_cli_parser(args=None):
    def url_file_or_folder(input: str) -> ParseResult | Path:
        parsed = urlparse(input)
        if all([parsed.scheme, parsed.netloc]):
            return parsed
        path = Path(input)
        if path.is_file():
            return path
        if path.is_dir():
            return path
        raise argparse.ArgumentTypeError(
            f"{input} is not a valid input. Must be a file, folder or sparql endpoint"
        )

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="{version}".format(version=__version__),
    )

    group.add_argument(
        "-o",
        "--output",
        help="The form of output you want",
        choices=["iris", "rdf", "manifest"],
        default="manifest",
    )

    parser.add_argument(
        "-a",
        "--additional-context",
        help="File, Folder or Sparql Endpoint to read additional context RDF from",
        type=url_file_or_folder,
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

    x = label(args.manifest, args.output, args.additional_context)

    if args.output == "iris":
        print("\n".join([str(iri) for iri in x]))
    elif args.output == "rdf":
        if x is not None:
            print(x.serialize(format="longturtle"))

    else:  # manifest
        pass


if __name__ == "__main__":
    retval = cli(sys.argv[1:])
    if retval is not None:
        sys.exit(retval)

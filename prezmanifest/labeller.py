"""
Assesses a given Manifest, finds any IRIs in any of the given resources missing labels and tries to patch them from
a given source of labels, such as KurrawongAI's Semantic Background (https://github.com/kurrawong/semantic-background)
repository.
"""

from enum import Enum
from pathlib import Path

import httpx
from kurra.utils import load_graph
from labelify import extract_labels, find_missing_labels
from rdflib import BNode, Graph, Literal
from rdflib.namespace import PROF, RDF

from prezmanifest.definednamespaces import MRR, PREZ
from prezmanifest.utils import get_manifest_paths_and_graph, denormalise_artifacts


class LabellerOutputTypes(str, Enum):
    iris = "iris"
    rdf = "rdf"
    manifest = "manifest"


def label(
    manifest: Path,
    output_type: LabellerOutputTypes = LabellerOutputTypes.manifest,
    additional_context: Path | str | Graph = None,
    http_client: httpx.Client = None,
) -> set | Graph | None:
    """ "Main function for labeller module"""
    if not isinstance(output_type, LabellerOutputTypes):
        raise ValueError(
            f"Invalid output_type value, must be one of {', '.join([x for x in LabellerOutputTypes])}"
        )

    # create the target from the Manifest
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )

    content_graph = Graph()
    context_graph = Graph()

    artifacts = denormalise_artifacts((manifest_path, manifest_root, manifest_graph))

    for k, v in artifacts.items():
        if v["role"] in [MRR.CatalogueData, MRR.ResourceData]:
            content_graph += load_graph(k)
        elif v["role"] in [
            MRR.CompleteCatalogueAndResourceLabels,
            MRR.IncompleteCatalogueAndResourceLabels,
        ]:
            context_graph += load_graph(k)

    # add labels for system IRIs
    context_graph.parse(Path(__file__).parent / "system-labels.ttl")

    if output_type == LabellerOutputTypes.iris:
        combined_graph = manifest_graph + content_graph + context_graph

        iris_missing_labels = find_missing_labels(
            combined_graph, additional_context, http_client=http_client
        )

        return iris_missing_labels

    elif output_type == LabellerOutputTypes.rdf:
        if additional_context is None:
            raise ValueError("You must provide additional context")

        combined_graph = manifest_graph + content_graph + context_graph

        iris_missing_labels = find_missing_labels(
            combined_graph, http_client=http_client
        )

        return extract_labels(iris_missing_labels, additional_context, http_client)

    else:  # output_type == LabellerOutputTypes.manifest
        # If this is selected, generate the "rdf" output and create a resource for it in the Manifest
        # If there are no more missing labels then we have a mrr:CompleteCatalogueAndResourceLabels
        # else add mrr:IncompleteCatalogueAndResourceLabels

        # Generate labels for any IRIs missing them, using context given in the Manifest and any
        # Additional Context supplied

        rdf_addition = label(manifest, LabellerOutputTypes.rdf, additional_context)

        if len(rdf_addition) > 0:
            new_artifact = manifest.parent / "labels-additional.ttl"
            rdf_addition.serialize(destination=new_artifact, format="longturtle")
            new_resource = BNode()

            # Add to the Manifest
            manifest_iri = manifest_graph.value(
                predicate=RDF.type, object=PREZ.Manifest
            )
            manifest_graph.add((manifest_iri, PROF.hasResource, new_resource))
            manifest_graph.add(
                (new_resource, PROF.hasRole, MRR.IncompleteCatalogueAndResourceLabels)
            )
            manifest_graph.add(
                (new_resource, PROF.hasArtifact, Literal(new_artifact.name))
            )

            manifest_graph.serialize(destination=manifest, format="longturtle")
        else:
            raise Warning(
                "No new labels have been generated for content in this Manifest. "
                "This could be because none were missing or because no new labels can be found in any "
                "supplied additional context."
            )

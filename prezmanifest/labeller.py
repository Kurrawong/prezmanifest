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
from rdflib.namespace import PROF

from prezmanifest.definednamespaces import MRR
from prezmanifest.loader import ReturnDatatype, load
from prezmanifest.utils import get_files_from_artifact


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
    # create the target from the Manifest
    manifest_content_graph = load(manifest, return_data_type=ReturnDatatype.graph)

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

    # add labels for system IRIs
    context_graph.parse(Path(__file__).parent / "system-labels.ttl")

    if not isinstance(output_type, LabellerOutputTypes):
        raise ValueError(
            f"Invalid output_type value, must be one of {', '.join([x for x in LabellerOutputTypes])}"
        )

    if output_type == LabellerOutputTypes.iris:
        return find_missing_labels(
            manifest_content_graph + context_graph,
            additional_context,
            http_client=http_client
        )

    elif output_type == LabellerOutputTypes.rdf:
        iris = find_missing_labels(
            manifest_content_graph,
            context_graph,
            http_client=http_client
        )

        if additional_context is not None:
            return extract_labels(iris, additional_context, http_client)
        else:
            return None

    else:  # output_type == LabellerOutputTypes.manifest
        # If this is selected, generate the "rdf" output and create a resource for it in the Manifest
        # If there are no more missing labels then we have a mrr:CompleteCatalogueAndResourceLabels
        # else add mrr:IncompleteCatalogueAndResourceLabels

        # Generate labels for any IRIs missing them, using context given in the Manifest and any
        # Additional Context supplied

        manifest_only_graph = load_graph(manifest)
        rdf_addition = label(manifest, LabellerOutputTypes.rdf, additional_context)

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

            if (
                MRR.CompleteCatalogueAndResourceLabels in context_roles
                and len(context_roles) == 1
            ):
                # If a CompleteCatalogueAndResourceLabels is present in Manifest and yet more labels were discovered,
                # change CompleteCatalogueAndResourceLabels to IncompleteCatalogueAndResourceLabels and add another
                for s, o in manifest_content_graph.subject_objects(PROF.hasRole):
                    if o == MRR.CompleteCatalogueAndResourceLabels:
                        manifest_only_graph.remove((s, PROF.hasRole, o))
                        manifest_only_graph.add(
                            (manifest_iri, PROF.hasResource, new_resource)
                        )
                        manifest_only_graph.add(
                            (
                                new_resource,
                                PROF.hasRole,
                                MRR.IncompleteCatalogueAndResourceLabels,
                            )
                        )
                        manifest_only_graph.add(
                            (new_resource, PROF.hasArtifact, Literal(new_artifact.name))
                        )
            else:
                # If an IncompleteCatalogueAndResourceLabels was present, add another IncompleteCatalogueAndResourceLabels
                # which together make a CompleteCatalogueAndResourceLabels

                # If none was present, add an IncompleteCatalogueAndResourceLabels or a CompleteCatalogueAndResourceLabels
                # TODO: test for completeness of labelling and add in CompleteCatalogueAndResourceLabels if complete
                manifest_only_graph.add((manifest_iri, PROF.hasResource, new_resource))
                manifest_only_graph.add(
                    (
                        new_resource,
                        PROF.hasRole,
                        MRR.IncompleteCatalogueAndResourceLabels,
                    )
                )
                manifest_only_graph.add(
                    (new_resource, PROF.hasArtifact, Literal(new_artifact.name))
                )

            manifest_only_graph.serialize(destination=manifest, format="longturtle")
        else:
            raise Warning(
                "No new labels have been generated for content in this Manifest. "
                "This could be because none were missing or because no new labels can be found in any "
                "supplied additional context."
            )

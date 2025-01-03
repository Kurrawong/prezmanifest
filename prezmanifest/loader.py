"""
Either creates an n-quads files containing the content of a Manifest file or uploads the content to Fuseki.

It creates:

 1. A Named Graph for each resource using the item's IRI as the graph IRI
 2. A Named Graph for the catalogue, either using the catalogue's IRI as the graph IRI + "-catalogue" if given, or by making one up - a Blank Node
 3. All the triples in resources with roles mrr:CompleteCatalogueAndResourceLabels & mrr:IncompleteCatalogueAndResourceLabels within a Named Graph with IRI <https://background>
 4. An Olis Virtual Graph, <https://olis.dev/VirtualGraph> object using the catalogue IRI, if give, which is as an alias for all the Named Graphs from 1., 2. & 3.
 5. Multiple entries in the System Graph - Named Graph with IRI <https://olis.dev/SystemGraph> - for each Named and the Virtual Graph from 1., 2. & 3.

Run this script with the -h flag for more help, i.e. ~$ python loader.py -h
"""

import argparse
import sys
from pathlib import Path

from kurra.format import make_dataset, export_quads
from kurra.fuseki import upload
from kurra.utils import load_graph
from rdflib import DCAT, DCTERMS, OWL, PROF, RDF, SDO, SKOS
from rdflib import Graph, URIRef, Dataset
from typing import Literal as TLiteral
import logging

try:
    from prezmanifest import MRR, OLIS, validate, __version__
    from prezmanifest.utils import get_files_from_artifact
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).parent.parent.resolve()))
    from prezmanifest import MRR, OLIS, validate, __version__
    from prezmanifest.utils import get_files_from_artifact


def load(
    manifest: Path,
    sparql_endpoint: str = None,
    destination_file: Path = None,
    return_data_type: TLiteral["Graph", "Dataset", None] = None
) -> None | Graph | Dataset:
    """Loads a catalogue of data from a prezmanifest file, whose content are valid according to the Prez Manifest Model
    (https://kurrawong.github.io/prez.dev/manifest/) either into a specified quads file in the Trig format, or into a
    given SPARQL Endpoint."""

    if return_data_type == "Dataset":
        dataset_holder = Dataset()

    if return_data_type == "Graph":
        graph_holder = Graph()

    return_data_value_error_message = "return_data_type was set to an invalid value. Must be one of Dataset or Graph or None"

    def _export(data: Graph | Dataset, iri, sparql_endpoint, destination_file, return_data_type, append=False):
        if type(data) is Dataset:
            if iri is not None:
                raise ValueError("If the data is a Dataset, the parameter iri must be None")

            if destination_file is not None:
                export_quads(data, destination_file)
            elif sparql_endpoint is not None:
                for g in data.graphs():
                    if g.identifier != URIRef("urn:x-rdflib:default"):
                        _export(g, g.identifier, sparql_endpoint, None, None)
            else:
                if return_data_type == "Dataset":
                    return data
                elif return_data_type == "Graph":
                    gx = Graph()
                    for g in data.graphs():
                        if g.identifier != URIRef("urn:x-rdflib:default"):
                            for s, p, o in g.triples((None, None, None)):
                                gx.add((s, p, o))
                    return gx

        elif type(data) is Graph:
            if iri is None:
                raise ValueError("If the data is a GRaph, the parameter iri must not be None")

            msg = f"exporting {iri} "
            if destination_file is not None:
                msg += f"to file {destination_file} "
                export_quads(make_dataset(data, iri), destination_file)
            elif sparql_endpoint is not None:
                msg += f"to SPARQL Endpoint {sparql_endpoint}"
                upload(sparql_endpoint, data, iri, append)
            else:  # returning data
                if return_data_type == "Dataset":
                    msg += "to Dataset"
                    for s, p, o in data:
                        dataset_holder.add((s, p, o, iri))
                elif return_data_type == "Graph":
                    msg += "to Graph"
                    for s, p, o in data:
                        graph_holder.add((s, p, o))
                else:
                    raise ValueError(return_data_value_error_message)

            logging.info(msg)

    if sum(x is not None for x in [sparql_endpoint, destination_file, return_data_type]) != 1:
        raise ValueError(
            "You must specify exactly 1 of sparql_endpoint, destination_file or return_data_type",
        )

    MANIFEST_ROOT_DIR = manifest.parent
    # load and validate manifest
    validate(manifest)
    manifest_graph = load_graph(manifest)

    vg = Graph()
    vg_iri = None

    for s, o in manifest_graph.subject_objects(PROF.hasResource):
        for role in manifest_graph.objects(o, PROF.hasRole):
            # The catalogue - must be processed first
            if role == MRR.CatalogueData:
                for artifact in manifest_graph.objects(o, PROF.hasArtifact):
                    # load the Catalogue, determine the Virtual Graph & Catalogue IRIs
                    # and fail if we can't see a Catalogue object
                    c = load_graph(MANIFEST_ROOT_DIR / str(artifact))
                    vg_iri = c.value(predicate=RDF.type, object=DCAT.Catalog)
                    if vg_iri is None:
                        raise ValueError(
                            f"ERROR: Could not create a Virtual Graph as no Catalog found in the Catalogue data"
                        )
                    catalogue_iri = URIRef(str(vg_iri) + "-catalogue")

                    # add to the System Graph
                    vg.add((vg_iri, RDF.type, OLIS.VirtualGraph))
                    vg.add((vg_iri, OLIS.isAliasFor, catalogue_iri))
                    vg_name = c.value(
                        subject=vg_iri,
                        predicate=SDO.name | DCTERMS.title | SKOS.prefLabel,
                    ) or str(vg_iri)
                    vg.add((vg_iri, SDO.name, vg_name))

                    # export the Catalogue data
                    _export(c, catalogue_iri, sparql_endpoint, destination_file, return_data_type)

        # non-catalogue resources
        for s, o in manifest_graph.subject_objects(PROF.hasResource):
            for role in manifest_graph.objects(o, PROF.hasRole):
                # The data files & background - must be processed after Catalogue
                if role in [
                    MRR.CompleteCatalogueAndResourceLabels,
                    MRR.IncompleteCatalogueAndResourceLabels,
                    MRR.ResourceData,
                ]:
                    for artifact in manifest_graph.objects(o, PROF.hasArtifact):
                        for f in get_files_from_artifact(manifest, artifact):
                            if str(f.name).endswith(".ttl"):
                                fg = Graph().parse(f)
                                # fg.bind("rdf", RDF)

                                if role == MRR.ResourceData:
                                    resource_iri = fg.value(predicate=RDF.type, object=SKOS.ConceptScheme) or fg.value(predicate=RDF.type, object=OWL.Ontology)

                                if role in [
                                    MRR.CompleteCatalogueAndResourceLabels,
                                    MRR.IncompleteCatalogueAndResourceLabels,
                                ]:
                                    resource_iri = URIRef("http://background")

                                if resource_iri is None:
                                    raise ValueError(f"Could not determine Resource IRI for file {f}")

                                vg.add((vg_iri, OLIS.isAliasFor, resource_iri))

                                # export one Resource
                                _export(fg, resource_iri, sparql_endpoint, destination_file, return_data_type)
                            elif str(f.name).endswith(".trig"):
                                d = Dataset()
                                d.parse(f)
                                for g in d.graphs():
                                    if g.identifier != URIRef("urn:x-rdflib:default"):
                                        vg.add((vg_iri, OLIS.isAliasFor, g.identifier))
                                _export(d, None, sparql_endpoint, destination_file, return_data_type)


        # export the System Graph
        _export(vg, OLIS.SystemGraph, sparql_endpoint, destination_file, return_data_type, append=True)

    if return_data_type == "Dataset":
        return dataset_holder
    elif return_data_type == "Graph":
        return graph_holder
    elif return_data_type is None:
        pass  # return nothing
    else:
        raise ValueError(return_data_value_error_message)


def setup_cli_parser(args=None):
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="{version}".format(version=__version__),
    )

    group.add_argument(
        "-e",
        "--endpoint",
        help="The SPARQL endpoint you want to load the data into. Cannot be specified when destination is.",
    )

    group.add_argument(
        "-d",
        "--destination",
        help="The n-quads file you want to export the data into. Cannot be specified when endpoint is.",
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

    load(
        Path(args.manifest),
        args.endpoint if args.endpoint is not None else None,
        Path(args.destination) if args.destination is not None else None,
    )


if __name__ == "__main__":
    retval = cli(sys.argv[1:])
    if retval is not None:
        sys.exit(retval)

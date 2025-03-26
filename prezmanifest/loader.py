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

import logging
import sys
from enum import Enum
from getpass import getpass
from pathlib import Path

import httpx
from kurra.db import upload
from kurra.file import export_quads, make_dataset
from kurra.utils import load_graph
from rdflib import DCTERMS, PROF, RDF, SDO, SKOS, Dataset, Graph, URIRef

from prezmanifest.definednamespaces import MRR, OLIS
from prezmanifest.utils import (
    KNOWN_ENTITY_CLASSES,
    get_files_from_artifact,
    get_catalogue_iri_from_manifest,
)
from prezmanifest.utils import get_manifest_paths_and_graph


class ReturnDatatype(str, Enum):
    graph = "graph"
    dataset = "dataset"
    none = None


def load(
    manifest: Path | tuple[Path, Path, Graph],
    sparql_endpoint: str = None,
    sparql_username: str = None,
    sparql_password: str = None,
    destination_file: Path = None,
    return_data_type: ReturnDatatype = ReturnDatatype.none,
) -> None | Graph | Dataset:
    """Loads a catalogue of data from a prezmanifest file, whose content are valid according to the Prez Manifest Model
    (https://kurrawong.github.io/prez.dev/manifest/) either into a specified quads file in the Trig format, or into a
    given SPARQL Endpoint."""

    # validate and load
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )

    catalogue_iri_orig = get_catalogue_iri_from_manifest(
        (manifest_path, manifest_root, manifest_graph)
    )
    vg_iri = catalogue_iri_orig
    catalogue_iri = URIRef(str(catalogue_iri_orig) + "-catalogue")

    if not isinstance(return_data_type, ReturnDatatype):
        raise ValueError(
            f"Invalid return_data_type value. Must be one of {', '.join([x for x in ReturnDatatype])}"
        )

    if (
        sparql_endpoint is None
        and destination_file is None
        and return_data_type == ReturnDatatype.none
    ):
        raise ValueError(
            "Either a sparql_endpoint, destination_file or a return_data_type must be specified"
        )

    if return_data_type == ReturnDatatype.dataset:
        dataset_holder = Dataset()

    if return_data_type == ReturnDatatype.graph:
        graph_holder = Graph()

    # establish a reusable client for http requests
    # also allows for basic authentication to be used
    if sparql_endpoint:
        auth = None
        if sparql_username:
            if not sparql_password:
                if not sys.stdin.isatty():
                    # if not possible to prompt for a password
                    raise ValueError(
                        "A password must be given if a sparql username is set"
                    )
                sparql_password = getpass()
            auth = httpx.BasicAuth(sparql_username, sparql_password)
        http_client = httpx.Client(base_url=sparql_endpoint, auth=auth)
    else:
        http_client = None

    def _export(
        data: Graph | Dataset,
        iri,
        http_client: httpx.Client | None,
        sparql_endpoint,
        destination_file,
        return_data_type,
        append=False,
    ):
        if type(data) is Dataset:
            if iri is not None:
                raise ValueError(
                    "If the data is a Dataset, the parameter iri must be None"
                )

            if destination_file is not None:
                export_quads(data, destination_file)
            elif sparql_endpoint is not None:
                for g in data.graphs():
                    if g.identifier != URIRef("urn:x-rdflib:default"):
                        _export(
                            data=g,
                            iri=g.identifier,
                            http_client=http_client,
                            destination_file=None,
                            return_data_type=None,
                        )
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
                raise ValueError(
                    "If the data is a GRaph, the parameter iri must not be None"
                )

            msg = f"exporting {iri} "
            if destination_file is not None:
                msg += f"to file {destination_file} "
                export_quads(make_dataset(data, iri), destination_file)
            elif sparql_endpoint is not None:
                msg += f"to SPARQL Endpoint {sparql_endpoint}"
                upload(
                    sparql_endpoint=sparql_endpoint,
                    file_or_str_or_graph=data,
                    graph_id=iri,
                    append=append,
                    http_client=http_client,
                )
            else:  # returning data
                if return_data_type == ReturnDatatype.dataset:
                    msg += "to Dataset"
                    for s, p, o in data:
                        dataset_holder.add((s, p, o, iri))
                elif return_data_type == ReturnDatatype.graph:
                    msg += "to Graph"
                    for s, p, o in data:
                        graph_holder.add((s, p, o))

            logging.info(msg)

    count = 0
    if sparql_endpoint is not None:
        count += 1

    if destination_file is not None:
        count += 1

    if return_data_type != ReturnDatatype.none:
        count += 1

    if count != 1:
        raise ValueError(
            "You must specify exactly 1 of sparql_endpoint, destination_file or return_data_type",
        )

    vg = Graph()

    for s, o in manifest_graph.subject_objects(PROF.hasResource):
        for role in manifest_graph.objects(o, PROF.hasRole):
            # The catalogue - must be processed first
            if role == MRR.CatalogueData:
                for artifact in manifest_graph.objects(o, PROF.hasArtifact):
                    # load the Catalogue, determine the Virtual Graph & Catalogue IRIs
                    # and fail if we can't see a Catalogue object
                    catalogue_graph = load_graph(manifest_root / artifact)

                    if vg_iri is None:
                        raise ValueError(
                            "ERROR: Could not create a Virtual Graph as no Catalog found in the Catalogue data"
                        )

                    # add to the System Graph
                    vg.add((vg_iri, RDF.type, OLIS.VirtualGraph))
                    vg.add((vg_iri, OLIS.isAliasFor, catalogue_iri))
                    vg_name = catalogue_graph.value(  # type: ignore
                        subject=vg_iri,
                        predicate=SDO.name | DCTERMS.title | SKOS.prefLabel,
                    ) or str(vg_iri)
                    vg.add((vg_iri, SDO.name, vg_name))

                    # export the Catalogue data
                    _export(
                        data=catalogue_graph,
                        iri=catalogue_iri,
                        http_client=http_client,
                        sparql_endpoint=sparql_endpoint,
                        destination_file=destination_file,
                        return_data_type=return_data_type,
                    )

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
                    for f in get_files_from_artifact(
                        (manifest_path, manifest_root, manifest_graph), artifact
                    ):
                        if str(f.name).endswith(".ttl"):
                            try:
                                fg = Graph().parse(f)
                            except Exception as e:
                                raise ValueError(
                                    f"Could not load file {f}. Error is {e}"
                                )

                            # fg.bind("rdf", RDF)

                            if role == MRR.ResourceData:
                                resource_iri = fg.value(
                                    subject=artifact, predicate=SDO.mainEntity
                                )
                                if resource_iri is None:
                                    for entity_class in KNOWN_ENTITY_CLASSES:
                                        v = fg.value(
                                            predicate=RDF.type, object=entity_class
                                        )
                                        if v is not None:
                                            resource_iri = v

                            if role in [
                                MRR.CompleteCatalogueAndResourceLabels,
                                MRR.IncompleteCatalogueAndResourceLabels,
                            ]:
                                resource_iri = URIRef("http://background")

                            if resource_iri is None:
                                raise ValueError(
                                    f"Could not determine Resource IRI for file {f}"
                                )

                            vg.add((vg_iri, OLIS.isAliasFor, resource_iri))

                            # export one Resource
                            _export(
                                data=fg,
                                iri=resource_iri,
                                http_client=http_client,
                                sparql_endpoint=sparql_endpoint,
                                destination_file=destination_file,
                                return_data_type=return_data_type,
                            )
                        elif str(f.name).endswith(".trig"):
                            d = Dataset()
                            d.parse(f)
                            for g in d.graphs():
                                if g.identifier != URIRef("urn:x-rdflib:default"):
                                    vg.add((vg_iri, OLIS.isAliasFor, g.identifier))
                            _export(
                                data=d,
                                iri=None,
                                http_client=http_client,
                                sparql_endpoint=sparql_endpoint,
                                destination_file=destination_file,
                                return_data_type=return_data_type,
                            )

        # export the System Graph
        _export(
            data=vg,
            iri=OLIS.SystemGraph,
            http_client=http_client,
            sparql_endpoint=sparql_endpoint,
            destination_file=destination_file,
            return_data_type=return_data_type,
            append=True,
        )

    if return_data_type == ReturnDatatype.dataset:
        return dataset_holder
    elif return_data_type == ReturnDatatype.graph:
        return graph_holder
    else:  # return_data_type is None:
        pass  # return nothing

"""
This script creates a "Prez Resources" table in either Markdown or ASCIIDOC from a Manifest file which it validates first

Run this script with the -h flag for more help, i.e. ~$ python documentor.py -h

Example:

Input:

PREFIX mrr: <https://prez.dev/ManifestResourceRoles/>
PREFIX prez: <https://prez.dev/>
PREFIX prof: <http://www.w3.org/ns/dx/prof/>
PREFIX schema: <https://schema.org/>

[]
    a prez:Manifest ;
    prof:hasResource
        [
            prof:hasArtifact "catalogue.ttl" ;
            prof:hasRole mrr:ContainerData ;
            schema:description "The definition of, and medata for, the container which here is a dcat:Catalog object" ;
            schema:name "Catalogue Definition"
        ] ,
        [
            prof:hasArtifact "vocabs/*.ttl" ;
            prof:hasRole mrr:ContentData ;
            schema:description "skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder" ;
            schema:name "Content"
        ] ,
        [
            prof:hasArtifact "https://github.com/RDFLib/prez/blob/main/prez/reference_data/profiles/ogc_records_profile.ttl" ;
            prof:hasRole mrr:ContainerAndContentModel ;
            schema:description "The default Prez profile for Records API" ;
            schema:name "Profile Definition"
        ] ,
        [
            prof:hasArtifact "_background/labels.ttl" ;
            prof:hasRole mrr:CompleteContainerAndContentLabels ;
            schema:description "An RDF file containing all the labels for the container content" ;
        ] ;
    .

Output:

Resource | Role | Description
--- | --- | ---
Catalogue Definition, [`catalogue.ttl`](catalogue.ttl) | [Container Data](https://prez.dev/ManifestResourceRoles/ContainerData) | The definition of, and medata for, the container which here is a dcat:Catalog object
Content, [`vocabs/*.ttl`](vocabs/*.ttl) | [Content Data](https://prez.dev/ManifestResourceRoles/ContentData) | skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder
Profile Definition, [`ogc_records_profile.ttl`](https://github.com/RDFLib/prez/blob/main/prez/reference_data/profiles/ogc_records_profile.ttl) | [Container & Content Model](https://prez.dev/ManifestResourceRoles/ContainerAndContentModel) | The default Prez profile for Records API
Labels file, [`_background/labels.ttl`](_background/labels.ttl) | [Complete Content and Container Labels](https://prez.dev/ManifestResourceRoles/CompleteContainerAndContentLabels) | An RDF file containing all the labels for the container content
"""

import argparse
import sys
from enum import Enum
from pathlib import Path
from textwrap import dedent
from urllib.parse import ParseResult, urlparse

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCAT, PROF, RDF, SDO, SKOS

from prezmanifest import __version__
from prezmanifest.definednamespaces import MRR
from prezmanifest.utils import (
    get_files_from_artifact,
    get_identifier_from_file,
    load_graph,
)
from prezmanifest.validator import validate


class TableFormats(str, Enum):
    asciidoc = "asciidoc"
    markdown = "markdown"


def table(manifest: Path, t="markdown") -> str:
    # load and validate manifest
    validate(manifest)
    manifest_graph = load_graph(manifest)

    # add in MRR vocab
    manifest_graph += load_graph(Path(__file__).parent / "mrr.ttl")

    if t == "asciidoc":
        header = "|===\n| Resource | Role | Description\n\n"
    else:
        header = "Resource | Role | Description\n--- | --- | ---\n"

    body = ""
    for s, o in manifest_graph.subject_objects(PROF.hasResource):
        artifact_docs = []
        for artifact in manifest_graph.objects(o, PROF.hasArtifact):
            if isinstance(artifact, Literal):
                a = str(artifact)
            else:  # isinstance( a, BNode)
                a = str(
                    manifest_graph.value(
                        subject=artifact, predicate=SDO.contentLocation
                    )
                )
            if t == "asciidoc":
                artifact_docs.append(
                    f"link:{a}[`{a.split('/')[-1] if a.startswith('http') else a}`]"
                )
            else:
                artifact_docs.append(
                    f"[`{a.split('/')[-1] if a.startswith('http') else a}`]({a})"
                )
        role_iri = manifest_graph.value(o, PROF.hasRole)
        role_label = manifest_graph.value(role_iri, SKOS.prefLabel)
        if t == "asciidoc":
            role = f"{role_iri}[{role_label}]"
        else:
            role = f"[{role_label}]({role_iri})"
        name = manifest_graph.value(o, SDO.name)
        description = manifest_graph.value(o, SDO.description)
        if t == "asciidoc":
            n = (
                f"""{name}: +
 +
* {
                    ''' +
* '''.join(artifact_docs)
                }"""
                if name is not None
                else f"{
                    ''' +
* '''.join(artifact_docs)
                }"
                ""
            )
        else:
            n = (
                f"{name}:<br />{'<br />'.join(artifact_docs)}"
                if name is not None
                else f"{'<br />'.join(artifact_docs)}"
            )
        d = description if description is not None else ""
        if t == "asciidoc":
            body += f"| {n} | {role} | {d}\n"
        else:
            body += f"{n} | {role} | {d}\n"

    if t == "asciidoc":
        footer = "|===\n"
    else:
        footer = ""

    return (header + body + footer).strip()


def catalogue(manifest: Path) -> Graph:
    MANIFEST_ROOT_DIR = manifest.parent
    # load and validate manifest
    validate(manifest)
    manifest_graph = load_graph(manifest)

    catalogue = Graph()
    for s, o in manifest_graph.subject_objects(PROF.hasResource):
        for role in manifest_graph.objects(o, PROF.hasRole):
            if role == MRR.CatalogueData:
                for artifact in manifest_graph.objects(o, PROF.hasArtifact):
                    # the artifact can only be a triples file (not a quads file)
                    catalogue = load_graph(MANIFEST_ROOT_DIR / artifact)

    # get the IRI of the catalogue
    catalogue_iri = catalogue.value(
        predicate=RDF.type, object=DCAT.Catalog
    ) or catalogue.value(predicate=RDF.type, object=SDO.DataCatalog)

    # non-catalogue resources
    for s, o in manifest_graph.subject_objects(PROF.hasResource):
        for role in manifest_graph.objects(o, PROF.hasRole):
            if role == MRR.ResourceData:
                for artifact in manifest_graph.objects(o, PROF.hasArtifact):
                    for f in get_files_from_artifact(
                        manifest_graph, manifest, artifact
                    ):
                        if isinstance(artifact, Literal):
                            for iri in sorted(get_identifier_from_file(f)):
                                if iri != URIRef("urn:x-rdflib:default"):
                                    catalogue.add((catalogue_iri, SDO.hasPart, iri))
                        else:  # isinstance(artifact, BNode):
                            iri = manifest_graph.value(
                                subject=artifact, predicate=SDO.mainEntity
                            )
                            catalogue.add((catalogue_iri, SDO.hasPart, iri))

    return catalogue

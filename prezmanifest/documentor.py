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
from pathlib import Path
from urllib.parse import ParseResult, urlparse

from rdflib import DCAT, DCTERMS, PROF, SDO, SKOS, Graph
from kurra.utils import load_graph

try:
    from prezmanifest import MRR, validate, __version__
    from prezmanifest.utils import *
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).parent.parent.resolve()))
    from prezmanifest import MRR, validate, __version__
    from prezmanifest.utils import *


def create_table(manifest: Path, t="markdown") -> str:
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
        a = str(manifest_graph.value(o, PROF.hasArtifact))
        if t == "asciidoc":
            artifact = f'link:{a}[`{a.split("/")[-1] if a.startswith("http") else a}`]'
        else:
            artifact = f'[`{a.split("/")[-1] if a.startswith("http") else a}`]({a})'
        role_iri = manifest_graph.value(o, PROF.hasRole)
        role_label = manifest_graph.value(role_iri, SKOS.prefLabel)
        if t == "asciidoc":
            role = f"{role_iri}[{role_label}]"
        else:
            role = f"[{role_label}]({role_iri})"
        name = manifest_graph.value(o, SDO.name)
        description = manifest_graph.value(o, SDO.description)
        n = f"{name}, {artifact}" if name is not None else f"{artifact}"
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


def create_catalogue(manifest: Path):
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
    catalogue_iri = catalogue.value(predicate=RDF.type, object=DCAT.Catalog)

    # non-catalogue resources
    for s, o in manifest_graph.subject_objects(PROF.hasResource):
        for role in manifest_graph.objects(o, PROF.hasRole):
            if role == MRR.ResourceData:
                for artifact in manifest_graph.objects(o, PROF.hasArtifact):
                    for f in get_files_from_artifact(manifest, artifact):
                        for iri in sorted(get_identifier_from_file(f)):
                            if iri != URIRef("urn:x-rdflib:default"):
                                catalogue.add((catalogue_iri, DCTERMS.hasPart, iri))

    return catalogue


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

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="{version}".format(version=__version__),
    )

    parser.add_argument(
        "function",
        help="The documentation function you wish to perform",
        choices=["table", "catalogue"],
    )

    parser.add_argument(
        "-t",
        "--type",
        help="The type of markup you want to export: Markdown or ASCCIDOC. Only relevant for the 'table' function",
        choices=["markdown", "asciidoc"],
        default="markdown",
    )

    parser.add_argument(
        "input",
        help="A Prez Manifest file",
        type=url_file_or_folder,
    )

    return parser.parse_args(args)


def cli(args=None):
    if args is None:
        args = sys.argv[1:]

    args = setup_cli_parser(args)

    if args.function == "table":
        print(create_table(args.input, t=args.type))
    else:
        print(create_catalogue(args.input).serialize(format="longturtle"))


if __name__ == "__main__":
    retval = cli(sys.argv[1:])
    if retval is not None:
        sys.exit(retval)

from collections.abc import Generator
from pathlib import Path

from kurra.file import load_graph
from rdflib import BNode, Dataset, Graph, Literal, Node, URIRef, Namespace
from rdflib.namespace import DCAT, OWL, RDF, SDO, SKOS, PROF

from prezmanifest.definednamespaces import PREZ, MRR

KNOWN_PROFILES = {
    URIRef("http://www.opengis.net/def/geosparql"): Path(__file__).parent
    / "validator-geosparql-1.1.ttl",
    URIRef("https://data.idnau.org/pid/cp"): Path(__file__).parent
    / "validator-idn-cp.ttl",
    URIRef("https://w3id.org/profile/vocpub"): Path(__file__).parent
    / "validator-vocpub-4.10.ttl",
}

KNOWN_ENTITY_CLASSES = [
    SKOS.ConceptScheme,
    OWL.Ontology,
    DCAT.Resource,
    SDO.CreativeWork,
    SDO.Dataset,
    SDO.DefinedTerm,
]


def get_files_from_artifact(
    manifest_graph: Graph, manifest: Path, artifact: Node
) -> list[Path] | Generator[Path]:
    """Returns an iterable (list or generator) of Path objects for files within an artifact literal.

    This function will correctly interpret artifacts such as 'file.ttl', '*.ttl', '**/*.trig' etc.
    """
    if isinstance(artifact, Literal):
        if "*" not in str(artifact):
            return [manifest.parent / Path(str(artifact))]
        else:
            artifact_str = str(artifact)
            glob_marker_location = artifact_str.find("*")
            glob_parts = [
                artifact_str[:glob_marker_location],
                artifact_str[glob_marker_location:],
            ]

            return Path(manifest.parent / Path(glob_parts[0])).glob(glob_parts[1])
    elif isinstance(artifact, BNode):
        contentLocation = manifest_graph.value(
            subject=artifact, predicate=SDO.contentLocation
        )
        return [manifest.parent / Path(str(contentLocation))]
    else:
        raise TypeError(f"Unsupported artifact type: {type(artifact)}")


def get_identifier_from_file(file: Path) -> list[URIRef]:
    """Returns a list if RDFLib graph identifier (URIRefs) from a triples or quads file
    for all owl:Ontology and skos:ConceptScheme objects"""
    if file.name.endswith(".ttl"):
        g = Graph().parse(file)
        for entity_class in KNOWN_ENTITY_CLASSES:
            v = g.value(predicate=RDF.type, object=entity_class)
            if v is not None:
                return [v]
    elif file.name.endswith(".trig"):
        gs = []
        d = Dataset()
        d.parse(file, format="trig")
        for g in d.graphs():
            gs.append(g.identifier)
        return gs
    else:
        return []


def get_validator(manifest: Path, iri_or_path: URIRef | Literal) -> Graph:
    """Returns a graph from either the path of a SHACL file or a known IRI->profile validator file"""
    if isinstance(iri_or_path, URIRef):
        if iri_or_path not in KNOWN_PROFILES.keys():
            raise ValueError(
                f"You have specified conformance to an unknown profile. Known profiles are {', '.join(KNOWN_PROFILES.keys())}"
            )
        return load_graph(KNOWN_PROFILES[iri_or_path])

    MANIFEST_ROOT_DIR = manifest.parent
    return load_graph(MANIFEST_ROOT_DIR / iri_or_path)


def get_manifest_path_and_graph(manifest: Path | tuple[Graph, Path]) -> (Path, Graph):
    if isinstance(manifest, Path):
        MANIFEST_ROOT_DIR = Path(manifest).parent.resolve()
        manifest_graph = load_graph(manifest)
    else:
        manifest_graph = manifest[0]
        MANIFEST_ROOT_DIR = manifest[1]

    return MANIFEST_ROOT_DIR, manifest_graph


def get_catalogue_iri_from_manifest(manifest: Path | tuple[Graph, Path]) -> URIRef:
    MANIFEST_ROOT_DIR, manifest_graph = get_manifest_path_and_graph(manifest)

    for m in manifest_graph.subjects(RDF.type, PREZ.Manifest):
        for r in manifest_graph.objects(m, PROF.hasResource):
            for role in manifest_graph.objects(r, PROF.hasRole):
                if role == MRR.CatalogueData:
                    a = manifest_graph.value(subject=r, predcate=PROF.hasArtifact)
                    if isinstance(a, Literal):
                        a_graph = load_graph(MANIFEST_ROOT_DIR / str(a))
                        return (a_graph.value( predicate=RDF.type, object=DCAT.Catalog)
                                or a_graph.value(predicate=RDF.type, object=SDO.DataCatalog))

    raise ValueError(f"No catalogue object IRI found in Manifest {MANIFEST_ROOT_DIR}")



def does_target_contain_this_catalogue(
    manifest: Path | Graph,
    sparql_endpoint: str = None,
    sparql_username: str = None,
    sparql_password: str = None,
    destination_file: Path = None,
) -> bool:
    MANIFEST_ROOT_DIR, manifest_graph = get_manifest_path_and_graph(manifest)

    # get the IRI of the catalogue from the manifest
    cat_iri = get_catalogue_iri_from_manifest(manifest)



    # check if the IRI is in the target
    pass
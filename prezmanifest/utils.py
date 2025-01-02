from pathlib import Path
from typing import List
from collections.abc import Generator
from rdflib import Literal, URIRef, Graph, Dataset
from rdflib.namespace import OWL, RDF, RDFS, SKOS


def get_files_from_artifact(manifest: Path, artifact: Literal) -> List[Path] | Generator[Path]:
    """Returns an iterable (list or generator) of Path objects for files within an artifact literal.

    This function will correctly interpret artifacts such as 'file.ttl', '*.ttl', '**/*.trig' etc."""
    if not "*" in str(artifact):
        return [manifest.parent / Path(str(artifact))]
    else:
        artifact_str = str(artifact)
        glob_marker_location = artifact_str.find("*")
        glob_parts = [artifact_str[:glob_marker_location], artifact_str[glob_marker_location:]]

        return Path(manifest.parent / Path(glob_parts[0])).glob(glob_parts[1])


def get_identifier_from_file(file: Path) -> List[URIRef]:
    """Returns a list if RDFLib graph identifier (URIRefs) from a triples or quads file
    for all owl:Ontology and skos:ConceptScheme objects"""
    if file.name.endswith(".ttl"):
        g = Graph().parse(file)
        return [
            g.value(predicate=RDF.type, object=SKOS.ConceptScheme) or
            g.value(predicate=RDF.type, object=OWL.Ontology)
        ]
    elif file.name.endswith(".trig"):
        gs = []
        d = Dataset()
        d.parse(file, format="trig")
        for g in d.graphs():
            gs.append(g.identifier)
        return gs
    else:
        return []
from pathlib import Path
from rdflib import Graph
from rdflib.namespace import RDF, SKOS

FILES_DIR = Path("something")

for f in FILES_DIR.glob("*.ttl"):
    g = Graph()
    g.parse(f)
    iri = g.value(predicate=RDF.type, object=SKOS.ConceptScheme)

    # print(f"{f.name}, {iri}")

    print(f"<{iri}> ,")
from pathlib import Path
from rdflib import Graph
from rdflib.compare import isomorphic

try:
    from prezmanifest import label
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent.parent.resolve()))
    from prezmanifest import load


def test_label_iris():
    try:
        label(
            Path(__file__).parent / "demo-vocabs/manifest-no-labels.ttl",
            output="x"
        )
    except ValueError as e:
        assert str(e) == "Parameter output is x but must be one of iris, rdf, manifest"

    iris = label(
        Path(__file__).parent / "demo-vocabs/manifest-no-labels.ttl",
        output="iris"
    )

    assert len(iris) == 27


    iris = label(
        Path(__file__).parent / "demo-vocabs/manifest.ttl",
        output="iris"
    )

    assert len(iris) == 4

    iris = label(
        Path(__file__).parent / "demo-vocabs/manifest-no-labels.ttl",
        output="iris",
        additional_context="http://localhost:3030/ds/query"
    )

    assert len(iris) == 3

    iris = label(
        Path(__file__).parent / "demo-vocabs/manifest-no-labels.ttl",
        output="iris",
        additional_context= Path(__file__).parent / "demo-vocabs/labels-2.ttl",
    )

    # static context file has 2 relevant IRIs, so should be 27 - 2 = 25
    assert len(iris) == 25


def test_label_rdf():
    rdf = label(
        Path(__file__).parent / "demo-vocabs/manifest.ttl",
        "rdf",
        "http://localhost:3030/ds/query"
    )

    assert len(rdf) == 0

    rdf = label(
        Path(__file__).parent / "demo-vocabs/manifest-no-labels.ttl",
        "rdf",
        "http://localhost:3030/ds/query"
    )

    assert len(rdf) == 54

    rdf = label(
        Path(__file__).parent / "demo-vocabs/manifest-no-labels.ttl",
        "rdf",
    )

    assert not rdf


def test_label_manifest():
    original_manifest_path = Path(__file__).parent / "demo-vocabs/manifest-no-labels.ttl"
    original_manifest_contents = original_manifest_path.read_text()

    label(
        Path(__file__).parent / "demo-vocabs/manifest-no-labels.ttl",
        # output="manifest" is default
        additional_context="http://localhost:3030/ds/query"
    )

    expected_updated_manifest = Graph().parse(
        data="""
        PREFIX mrr: <https://prez.dev/ManifestResourceRoles/>
        PREFIX prez: <https://prez.dev/>
        PREFIX prof: <http://www.w3.org/ns/dx/prof/>
        PREFIX schema: <https://schema.org/>
        
        []    a prez:Manifest ;
            prof:hasResource
                [
                    prof:hasArtifact "labels-additional.ttl" ;
                    prof:hasRole mrr:IncompleteCatalogueAndResourceLabels ;
                ] ,
                [
                    prof:hasArtifact "catalogue.ttl" ;
                    prof:hasRole mrr:CatalogueData ;
                    schema:description "The definition of, and medata for, the container which here is a dcat:Catalog object" ;
                    schema:name "Catalogue Definition" ;
                ] ,
                [
                    prof:hasArtifact "vocabs/*.ttl" ;
                    prof:hasRole mrr:ResourceData ;
                    schema:description "skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder" ;
                    schema:name "Resource Data" ;
                ] ,
                [
                    prof:hasArtifact "https://github.com/RDFLib/prez/blob/main/prez/reference_data/profiles/ogc_records_profile.ttl" ;
                    prof:hasRole mrr:CatalogueAndResourceModel ;
                    schema:description "The default Prez profile for Records API" ;
                    schema:name "Profile Definition" ;
                ] ; ;
        .
        """
    )

    resulting_manifest = Graph().parse(original_manifest_path)

    assert  isomorphic(resulting_manifest, expected_updated_manifest)

    # replace this test's results and with original
    Path(original_manifest_path.parent / "labels-additional.ttl").unlink()
    original_manifest_path.unlink()
    original_manifest_path.write_text(original_manifest_contents)
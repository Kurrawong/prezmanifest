from pathlib import Path

import pytest
from kurra.db import sparql, upload
from rdflib import Graph
from rdflib.compare import isomorphic
from typer.testing import CliRunner

from prezmanifest.cli import app
from prezmanifest.labeller import LabellerOutputTypes, label
from tests.fuseki.conftest import fuseki_container

runner = CliRunner()


def test_label_iris():
    with pytest.raises(ValueError):
        label(
            Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl",
            output_type="x",
        )

    iris = label(
        Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl",
        output_type=LabellerOutputTypes.iris,
    )

    assert len(iris) == 31

    iris = label(
        Path(__file__).parent / "demo-vocabs/manifest-labels-some.ttl",
        output_type=LabellerOutputTypes.iris,
    )

    assert len(iris) == 16

    iris = label(
        Path(__file__).parent / "demo-vocabs/manifest-labels-all.ttl",
        output_type=LabellerOutputTypes.iris,
    )

    assert len(iris) == 0


def test_label_iris_sparql(fuseki_container):
    SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"
    upload(
        SPARQL_ENDPOINT,
        Path(__file__).parent / "demo-vocabs/labels-some.ttl",
        graph_id="http://test",
    )

    iris = label(
        Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl",
        output_type=LabellerOutputTypes.iris,
        additional_context=SPARQL_ENDPOINT,
    )

    assert len(iris) == 15


def test_label_rdf_file():
    with pytest.raises(ValueError):
        label(
            Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl",
            output_type=LabellerOutputTypes.rdf,
        )

    rdf = label(
        Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl",
        output_type=LabellerOutputTypes.rdf,
        additional_context=Path(__file__).parent / "demo-vocabs/labels-some.ttl",
    )

    assert len(rdf) == 37


def test_label_rdf_sparql(fuseki_container):
    SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"

    sparql(SPARQL_ENDPOINT, "DROP SILENT GRAPH <http://test>")

    rdf = label(
        Path(__file__).parent / "demo-vocabs/manifest.ttl",
        LabellerOutputTypes.rdf,
        SPARQL_ENDPOINT,
    )

    assert len(rdf) == 0

    rdf = label(
        Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl",
        LabellerOutputTypes.rdf,
        SPARQL_ENDPOINT,
    )

    assert len(rdf) == 0

    upload(
        SPARQL_ENDPOINT,
        Path(__file__).parent / "demo-vocabs/labels-some.ttl",
        graph_id="http://test",
    )

    rdf = label(
        Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl",
        LabellerOutputTypes.rdf,
        SPARQL_ENDPOINT,
    )

    assert len(rdf) == 37

    sparql(SPARQL_ENDPOINT, "DROP GRAPH <http://test>")

    upload(
        SPARQL_ENDPOINT,
        Path(__file__).parent / "demo-vocabs/labels-all.ttl",
        graph_id="http://test",
    )

    rdf = label(
        Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl",
        LabellerOutputTypes.rdf,
        SPARQL_ENDPOINT,
    )

    assert len(rdf) == 63


def test_label_manifest(fuseki_container):
    SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"

    sparql(SPARQL_ENDPOINT, "DROP SILENT GRAPH <http://test>")

    upload(
        SPARQL_ENDPOINT,
        Path(__file__).parent / "demo-vocabs/_background/labels.ttl",
        graph_id="http://test",
    )

    original_manifest_path = (
        Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl"
    )
    original_manifest_contents = original_manifest_path.read_text()

    label(
        Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl",
        # output="manifest" is default
        additional_context=SPARQL_ENDPOINT,
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
                ] ;
        .
        """
    )

    resulting_manifest = Graph().parse(original_manifest_path)

    assert isomorphic(resulting_manifest, expected_updated_manifest)

    # replace this test's results and with original
    Path(original_manifest_path.parent / "labels-additional.ttl").unlink()
    original_manifest_path.unlink()
    original_manifest_path.write_text(original_manifest_contents)


def test_label_iris_mainEntity():
    iris = label(
        Path(__file__).parent / "demo-vocabs/manifest-mainEntity.ttl",
        output_type=LabellerOutputTypes.iris,
    )

    assert len(iris) == 14


def test_label_cli_iris():
    result = runner.invoke(
        app,
        [
            "label",
            "iris",
            str(Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl"),
        ],
    )
    assert len(result.stdout.splitlines()) == 31


def test_label_cli_rdf(fuseki_container):
    SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"

    sparql(SPARQL_ENDPOINT, "DROP GRAPH <http://test>")

    upload(
        SPARQL_ENDPOINT,
        Path(__file__).parent / "demo-vocabs/_background/labels.ttl",
        graph_id="http://test",
    )

    upload(
        SPARQL_ENDPOINT,
        Path(__file__).parent / "demo-vocabs/labels-2.ttl",
        graph_id="http://test",
        append=True,
    )

    result = runner.invoke(
        app,
        [
            "label",
            "rdf",
            str(Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl"),
            SPARQL_ENDPOINT,
        ],
    )
    assert len(Graph().parse(data=result.stdout, format="turtle")) == 52


# TODO: fix not working test
# def test_label_cli_manifest(fuseki_container):
#     SPARQL_ENDPOINT = f"http://localhost:{fuseki_container.get_exposed_port(3030)}/ds"
#
#     sparql(SPARQL_ENDPOINT, "DROP SILENT GRAPH <http://test>")
#
#     upload(
#         SPARQL_ENDPOINT,
#         Path(__file__).parent / "demo-vocabs/_background/labels.ttl",
#         graph_id="http://test",
#     )
#
#     original_manifest_path = (
#             Path(__file__).parent / "demo-vocabs/manifest-labels-none.ttl"
#     )
#     original_manifest_contents = original_manifest_path.read_text()
#
#     runner.invoke(
#         app,
#         [
#             "label",
#             "manifest",
#             str(original_manifest_path),
#             SPARQL_ENDPOINT
#         ],
#     )
#
#     expected_updated_manifest = Graph().parse(
#         data="""
#         PREFIX mrr: <https://prez.dev/ManifestResourceRoles/>
#         PREFIX prez: <https://prez.dev/>
#         PREFIX prof: <http://www.w3.org/ns/dx/prof/>
#         PREFIX schema: <https://schema.org/>
#
#         []    a prez:Manifest ;
#             prof:hasResource
#                 [
#                     prof:hasArtifact "labels-additional.ttl" ;
#                     prof:hasRole mrr:IncompleteCatalogueAndResourceLabels ;
#                 ] ,
#                 [
#                     prof:hasArtifact "catalogue.ttl" ;
#                     prof:hasRole mrr:CatalogueData ;
#                     schema:description "The definition of, and medata for, the container which here is a dcat:Catalog object" ;
#                     schema:name "Catalogue Definition" ;
#                 ] ,
#                 [
#                     prof:hasArtifact "vocabs/*.ttl" ;
#                     prof:hasRole mrr:ResourceData ;
#                     schema:description "skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder" ;
#                     schema:name "Resource Data" ;
#                 ] ,
#                 [
#                     prof:hasArtifact "https://raw.githubusercontent.com/RDFLib/prez/refs/heads/main/prez/reference_data/profiles/ogc_records_profile.ttl" ;
#                     prof:hasRole mrr:CatalogueAndResourceModel ;
#                     schema:description "The default Prez profile for Records API" ;
#                     schema:name "Profile Definition" ;
#                 ] ;
#         .
#         """
#     )
#
#     resulting_manifest = Graph().parse(original_manifest_path)
#
#     assert isomorphic(resulting_manifest, expected_updated_manifest)
#
#     # replace this test's results and with original
#     Path(original_manifest_path.parent / "labels-additional.ttl").unlink()
#     original_manifest_path.unlink()
#     original_manifest_path.write_text(original_manifest_contents)

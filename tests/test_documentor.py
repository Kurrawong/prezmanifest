from pathlib import Path
from textwrap import dedent

import pytest
from kurra.utils import load_graph
from rdflib.compare import isomorphic
from typer.testing import CliRunner

from prezmanifest.cli import app
from prezmanifest.documentor import TableFormats, catalogue, table
from prezmanifest.validator import ManifestValidationError

runner = CliRunner()


def test_create_table_01():
    expected = dedent(
        """
        Resource | Role | Description
        --- | --- | ---
        Catalogue Definition:<br />[`catalogue.ttl`](catalogue.ttl) | [Catalogue Data](https://prez.dev/ManifestResourceRoles/CatalogueData) | The definition of, and medata for, the container which here is a dcat:Catalog object
        Resource Data:<br />[`vocabs/*.ttl`](vocabs/*.ttl) | [Resource Data](https://prez.dev/ManifestResourceRoles/ResourceData) | skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder
        Profile Definition:<br />[`ogc_records_profile.ttl`](https://raw.githubusercontent.com/RDFLib/prez/refs/heads/main/prez/reference_data/profiles/ogc_records_profile.ttl) | [Catalogue & Resource Model](https://prez.dev/ManifestResourceRoles/CatalogueAndResourceModel) | The default Prez profile for Records API
        Labels:<br />[`_background/labels.ttl`](_background/labels.ttl) | [Complete Catalogue and Resource Labels](https://prez.dev/ManifestResourceRoles/CompleteCatalogueAndResourceLabels) | An RDF file containing all the labels for the container content                
        """
    ).strip()

    result = table(Path(__file__).parent / "demo-vocabs" / "manifest.ttl")

    print()
    print()
    print(expected)
    print()
    print()
    print(result)
    print()
    print()

    assert result == expected


def test_create_table_02():
    with pytest.raises(ManifestValidationError):
        table(Path(__file__).parent / "demo-vocabs" / "manifest-invalid-01.ttl")


def test_create_catalogue():
    expected = load_graph(Path(__file__).parent / "demo-vocabs" / "catalogue.ttl")
    actual = catalogue(Path(__file__).parent / "demo-vocabs" / "manifest-cat.ttl")

    assert isomorphic(actual, expected)


def test_create_table_multi():
    expected = dedent(
        """
        Resource | Role | Description
        --- | --- | ---
        Catalogue Definition:<br />[`catalogue-metadata.ttl`](catalogue-metadata.ttl) | [Catalogue Data](https://prez.dev/ManifestResourceRoles/CatalogueData) | The definition of, and medata for, the container which here is a dcat:Catalog object
        Resource Data:<br />[`vocabs/image-test.ttl`](vocabs/image-test.ttl)<br />[`vocabs/language-test.ttl`](vocabs/language-test.ttl) | [Resource Data](https://prez.dev/ManifestResourceRoles/ResourceData) | skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder
        Profile Definition:<br />[`ogc_records_profile.ttl`](https://raw.githubusercontent.com/RDFLib/prez/refs/heads/main/prez/reference_data/profiles/ogc_records_profile.ttl) | [Catalogue & Resource Model](https://prez.dev/ManifestResourceRoles/CatalogueAndResourceModel) | The default Prez profile for Records API
        Labels:<br />[`_background/labels.ttl`](_background/labels.ttl) | [Complete Catalogue and Resource Labels](https://prez.dev/ManifestResourceRoles/CompleteCatalogueAndResourceLabels) | An RDF file containing all the labels for the container content                
        """
    ).strip()

    result = table(Path(__file__).parent / "demo-vocabs" / "manifest-multi.ttl")

    print()
    print()
    print(expected)
    print()
    print()
    print(result)
    print()
    print()

    assert result == expected


def test_create_table_multi_asciidoc():
    expected = dedent(
        """
        |===
        | Resource | Role | Description
        
        | Catalogue Definition: +
         +
        * link:catalogue-metadata.ttl[`catalogue-metadata.ttl`] | https://prez.dev/ManifestResourceRoles/CatalogueData[Catalogue Data] | The definition of, and medata for, the container which here is a dcat:Catalog object
        | Resource Data: +
         +
        * link:vocabs/image-test.ttl[`vocabs/image-test.ttl`] +
        * link:vocabs/language-test.ttl[`vocabs/language-test.ttl`] | https://prez.dev/ManifestResourceRoles/ResourceData[Resource Data] | skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder
        | Profile Definition: +
         +
        * link:https://raw.githubusercontent.com/RDFLib/prez/refs/heads/main/prez/reference_data/profiles/ogc_records_profile.ttl[`ogc_records_profile.ttl`] | https://prez.dev/ManifestResourceRoles/CatalogueAndResourceModel[Catalogue & Resource Model] | The default Prez profile for Records API
        | Labels: +
         +
        * link:_background/labels.ttl[`_background/labels.ttl`] | https://prez.dev/ManifestResourceRoles/CompleteCatalogueAndResourceLabels[Complete Catalogue and Resource Labels] | An RDF file containing all the labels for the container content
        |===  
        """
    ).strip()

    result = table(
        Path(__file__).parent / "demo-vocabs" / "manifest-multi.ttl",
        table_format=TableFormats.asciidoc,
    )

    print()
    print()
    print(expected)
    print()
    print()
    print(result)
    print()
    print()

    assert result == expected


def test_create_table_main_entity():
    expected = dedent(
        """
        Resource | Role | Description
        --- | --- | ---
        Catalogue Definition:<br />[`catalogue.ttl`](catalogue.ttl) | [Catalogue Data](https://prez.dev/ManifestResourceRoles/CatalogueData) | The definition of, and medata for, the container which here is a dcat:Catalog object
        Resource Data:<br />[`vocabs/image-test.ttl`](vocabs/image-test.ttl)<br />[`vocabs/language-test.ttl`](vocabs/language-test.ttl) | [Resource Data](https://prez.dev/ManifestResourceRoles/ResourceData) | skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder
        Profile Definition:<br />[`ogc_records_profile.ttl`](https://raw.githubusercontent.com/RDFLib/prez/refs/heads/main/prez/reference_data/profiles/ogc_records_profile.ttl) | [Catalogue & Resource Model](https://prez.dev/ManifestResourceRoles/CatalogueAndResourceModel) | The default Prez profile for Records API
        Labels:<br />[`_background/labels.ttl`](_background/labels.ttl) | [Complete Catalogue and Resource Labels](https://prez.dev/ManifestResourceRoles/CompleteCatalogueAndResourceLabels) | An RDF file containing all the labels for the container content                
        """
    ).strip()

    result = table(Path(__file__).parent / "demo-vocabs" / "manifest-mainEntity.ttl")

    print()
    print()
    print(expected)
    print()
    print()
    print(result)
    print()
    print()

    assert result == expected


def test_create_catalogue_multi():
    expected = load_graph(Path(__file__).parent / "demo-vocabs" / "catalogue.ttl")
    actual = catalogue(Path(__file__).parent / "demo-vocabs" / "manifest-multi.ttl")

    assert isomorphic(actual, expected)


def test_create_catalogue_main_entity():
    expected = load_graph(Path(__file__).parent / "demo-vocabs" / "catalogue.ttl")
    actual = catalogue(
        Path(__file__).parent / "demo-vocabs" / "manifest-mainEntity.ttl"
    )

    assert isomorphic(actual, expected)


def test_table_cli():
    result = runner.invoke(
        app,
        [
            "document",
            "table",
            str(Path(__file__).parent / "demo-vocabs" / "manifest.ttl"),
        ],
    )
    actual = result.stdout

    assert "Catalogue Definition" in actual


def test_catalogue_cli():
    expected = load_graph(
        """
        PREFIX ns1: <http://purl.org/linked-data/registry#>
        PREFIX schema: <https://schema.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        <https://example.com/demo-vocabs>
            a schema:DataCatalog ;
            ns1:status <https://linked.data.gov.au/def/reg-statuses/experimental> ;
            schema:codeRepository "https://github.com/kurrawong/demo-vocabs" ;
            schema:creator <https://kurrawong.ai> ;
            schema:dateCreated "2023"^^xsd:gYear ;
            schema:dateModified "2024-10-16"^^xsd:date ;
            schema:description "A testing catalogue for the Prez Manifest Loader tool" ;
            schema:hasPart
                <https://example.com/demo-vocabs/image-test> ,
                <https://example.com/demo-vocabs/language-test> ;
            schema:name "Demo Vocabularies" ;
            schema:publisher <https://kurrawong.ai> ;
            schema:version "1.0.1" ;
        .        
        """
    )
    result = runner.invoke(
        app,
        [
            "document",
            "catalogue",
            str(Path(__file__).parent / "demo-vocabs" / "manifest.ttl"),
        ],
    )
    actual = load_graph(result.stdout)

    assert isomorphic(expected, actual)

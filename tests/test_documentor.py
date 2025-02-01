from pathlib import Path
from textwrap import dedent

import pytest
from rdflib import Graph
from rdflib.compare import isomorphic

from prezmanifest import create_table, create_catalogue


def test_create_table_01():
    expected = dedent(
        """
        Resource | Role | Description
        --- | --- | ---
        Catalogue Definition:<br />[`catalogue.ttl`](catalogue.ttl) | [Catalogue Data](https://prez.dev/ManifestResourceRoles/CatalogueData) | The definition of, and medata for, the container which here is a dcat:Catalog object
        Resource Data:<br />[`vocabs/*.ttl`](vocabs/*.ttl) | [Resource Data](https://prez.dev/ManifestResourceRoles/ResourceData) | skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder
        Profile Definition:<br />[`ogc_records_profile.ttl`](https://github.com/RDFLib/prez/blob/main/prez/reference_data/profiles/ogc_records_profile.ttl) | [Catalogue & Resource Model](https://prez.dev/ManifestResourceRoles/CatalogueAndResourceModel) | The default Prez profile for Records API
        Labels:<br />[`_background/labels.ttl`](_background/labels.ttl) | [Complete Catalogue and Resource Labels](https://prez.dev/ManifestResourceRoles/CompleteCatalogueAndResourceLabels) | An RDF file containing all the labels for the container content                
        """
    ).strip()

    result = create_table(Path(__file__).parent / "demo-vocabs" / "manifest.ttl")

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
    with pytest.raises(ValueError):
        create_table(Path(__file__).parent / "demo-vocabs" / "manifest-invalid-01.ttl")


def test_create_catalogue():
    expected = Graph().parse(Path(__file__).parent / "demo-vocabs" / "catalogue.ttl")
    actual = create_catalogue(
        Path(__file__).parent / "demo-vocabs" / "manifest-cat.ttl"
    )

    assert isomorphic(actual, expected)


def test_create_table_multi():
    expected = dedent(
        """
        Resource | Role | Description
        --- | --- | ---
        Catalogue Definition:<br />[`catalogue-metadata.ttl`](catalogue-metadata.ttl) | [Catalogue Data](https://prez.dev/ManifestResourceRoles/CatalogueData) | The definition of, and medata for, the container which here is a dcat:Catalog object
        Resource Data:<br />[`vocabs/image-test.ttl`](vocabs/image-test.ttl)<br />[`vocabs/language-test.ttl`](vocabs/language-test.ttl) | [Resource Data](https://prez.dev/ManifestResourceRoles/ResourceData) | skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder
        Profile Definition:<br />[`ogc_records_profile.ttl`](https://github.com/RDFLib/prez/blob/main/prez/reference_data/profiles/ogc_records_profile.ttl) | [Catalogue & Resource Model](https://prez.dev/ManifestResourceRoles/CatalogueAndResourceModel) | The default Prez profile for Records API
        Labels:<br />[`_background/labels.ttl`](_background/labels.ttl) | [Complete Catalogue and Resource Labels](https://prez.dev/ManifestResourceRoles/CompleteCatalogueAndResourceLabels) | An RDF file containing all the labels for the container content                
        """
    ).strip()

    result = create_table(Path(__file__).parent / "demo-vocabs" / "manifest-multi.ttl")

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
        * link:https://github.com/RDFLib/prez/blob/main/prez/reference_data/profiles/ogc_records_profile.ttl[`ogc_records_profile.ttl`] | https://prez.dev/ManifestResourceRoles/CatalogueAndResourceModel[Catalogue & Resource Model] | The default Prez profile for Records API
        | Labels: +
         +
        * link:_background/labels.ttl[`_background/labels.ttl`] | https://prez.dev/ManifestResourceRoles/CompleteCatalogueAndResourceLabels[Complete Catalogue and Resource Labels] | An RDF file containing all the labels for the container content
        |===  
        """
    ).strip()

    result = create_table(
        Path(__file__).parent / "demo-vocabs" / "manifest-multi.ttl", t="asciidoc"
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
        Profile Definition:<br />[`ogc_records_profile.ttl`](https://github.com/RDFLib/prez/blob/main/prez/reference_data/profiles/ogc_records_profile.ttl) | [Catalogue & Resource Model](https://prez.dev/ManifestResourceRoles/CatalogueAndResourceModel) | The default Prez profile for Records API
        Labels:<br />[`_background/labels.ttl`](_background/labels.ttl) | [Complete Catalogue and Resource Labels](https://prez.dev/ManifestResourceRoles/CompleteCatalogueAndResourceLabels) | An RDF file containing all the labels for the container content                
        """
    ).strip()

    result = create_table(
        Path(__file__).parent / "demo-vocabs" / "manifest-mainEntity.ttl"
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


def test_create_catalogue_multi():
    expected = Graph().parse(Path(__file__).parent / "demo-vocabs" / "catalogue.ttl")
    actual = create_catalogue(
        Path(__file__).parent / "demo-vocabs" / "manifest-multi.ttl"
    )

    assert isomorphic(actual, expected)


def test_create_catalogue_main_entity():
    expected = Graph().parse(Path(__file__).parent / "demo-vocabs" / "catalogue.ttl")
    actual = create_catalogue(
        Path(__file__).parent / "demo-vocabs" / "manifest-mainEntity.ttl"
    )

    assert isomorphic(actual, expected)

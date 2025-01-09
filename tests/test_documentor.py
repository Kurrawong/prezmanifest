from pathlib import Path
from textwrap import dedent

import pytest
from rdflib import Graph
from rdflib.compare import isomorphic

try:
    from prezmanifest import create_table, create_catalogue
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).parent.parent.resolve()))
    from prezmanifest import create_table, create_catalogue


def test_create_table_01():
    expected = dedent(
        """
        Resource | Role | Description
        --- | --- | ---
        Catalogue Definition, [`catalogue.ttl`](catalogue.ttl) | [Catalogue Data](https://prez.dev/ManifestResourceRoles/CatalogueData) | The definition of, and medata for, the container which here is a dcat:Catalog object
        Resource Data, [`vocabs/*.ttl`](vocabs/*.ttl) | [Resource Data](https://prez.dev/ManifestResourceRoles/ResourceData) | skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder
        Profile Definition, [`ogc_records_profile.ttl`](https://github.com/RDFLib/prez/blob/main/prez/reference_data/profiles/ogc_records_profile.ttl) | [Catalogue & Resource Model](https://prez.dev/ManifestResourceRoles/CatalogueAndResourceModel) | The default Prez profile for Records API
        Labels, [`_background/labels.ttl`](_background/labels.ttl) | [Complete Catalogue and Resource Labels](https://prez.dev/ManifestResourceRoles/CompleteCatalogueAndResourceLabels) | An RDF file containing all the labels for the container content                
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
    expected = dedent(
        """
        Resource | Role | Description
        --- | --- | ---
        Catalogue Definition, [`catalogue.ttl`](catalogue.ttl) | [Catalogue Data](https://prez.dev/ManifestResourceRoles/CatalogueData) | The definition of, and medata for, the container which here is a dcat:Catalog object
        Resource, [`vocabs/*.ttl`](vocabs/*.ttl) | [Resource Data](https://prez.dev/ManifestResourceRoles/ResourceData) | skos:ConceptScheme objects in RDF (Turtle) files in the vocabs/ folder
        Profile Definition, [`ogc_records_profile.ttl`](https://github.com/RDFLib/prez/blob/main/prez/reference_data/profiles/ogc_records_profile.ttl) | [Catalogue & Resource Model](https://prez.dev/ManifestResourceRoles/CatalogueAndResourceModel) | The default Prez profile for Records API
        Labels file, [`_background/labels.ttl`](_background/labels.ttl) | [Complete Catalogue and Resource Labels](https://prez.dev/ManifestResourceRoles/CompleteCatalogueAndResourceLabels) | An RDF file containing all the labels for the container content                
        """
    ).strip()

    with pytest.raises(ValueError):
        create_table(Path(__file__).parent / "demo-vocabs" / "manifest-invalid-01.ttl")


def test_create_catalogue():
    expected = Graph().parse(Path(__file__).parent / "demo-vocabs" / "catalogue.ttl")
    actual = create_catalogue(
        Path(__file__).parent / "demo-vocabs" / "manifest-cat.ttl"
    )

    assert isomorphic(actual, expected)

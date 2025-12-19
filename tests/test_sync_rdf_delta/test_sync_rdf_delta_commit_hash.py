from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from rdflib import RDF, SDO, Dataset, Graph, Literal, URIRef
from rdflib.compare import isomorphic

from prezmanifest import load
from prezmanifest.definednamespaces import OLIS
from prezmanifest.event.syncer import (
    _add_commit_hash_to_dataset,
    _generate_rdf_patch_body_add,
    _retrieve_commit_hash,
)
from prezmanifest.loader import ReturnDatatype


def test_add_commit_hash_to_dataset():
    manifest = Path(__file__).parent.parent / "demo-vocabs" / "manifest-mainEntity.ttl"
    commit_hash = "1234567890"
    ds = load(manifest, return_data_type=ReturnDatatype.dataset)
    ds = _add_commit_hash_to_dataset(commit_hash, ds)
    assert len(ds) == 178

    graph = ds.graph(OLIS.SystemGraph)
    vg_iri = graph.value(predicate=RDF.type, object=OLIS.VirtualGraph)
    version_object = graph.value(subject=vg_iri, predicate=SDO.version)
    assert version_object is not None

    data = """
        PREFIX mvt: <https://prez.dev/ManifestVersionTypes/>
        PREFIX schema: <https://schema.org/>
        
        [] schema:additionalType mvt:GitCommitHash ;
           schema:value "1234567890" .
    """
    expected_graph = Graph().parse(data=data, format="turtle")
    assert isomorphic(graph.cbd(version_object), expected_graph)


def test_add_commit_hash_to_dataset_raises_value_error():
    # No virtual graph raises ValueError.
    ds = Dataset()
    commit_hash = "1234567890"
    with pytest.raises(ValueError):
        _add_commit_hash_to_dataset(commit_hash, ds)


def test_retrieve_commit_hash_from_sparql_endpoint(monkeypatch: pytest.MonkeyPatch):
    content = (
        b'<https://example.com/demo-vocabs> <https://schema.org/version> "1234567890" .'
    )
    response = Mock(
        spec=httpx.Response,
        content=content,
        headers={"Content-Type": "application/n-triples"},
    )
    monkeypatch.setattr(httpx.Client, "post", Mock(return_value=response))
    with httpx.Client() as client:
        commit_hash = _retrieve_commit_hash(
            URIRef("https://example.com/demo-vocabs"), "", client
        )
        assert commit_hash == Literal("1234567890")


def test_generate_rdf_patch_body_add():
    data = """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        <urn:vocab> a skos:ConceptScheme .
    """
    ds = Dataset().parse(data=data, format="turtle")
    rdf_patch_body = "".join(_generate_rdf_patch_body_add(ds))
    assert (
        rdf_patch_body
        == "TX .\nA <urn:vocab> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2004/02/skos/core#ConceptScheme> .\nTC ."
    )

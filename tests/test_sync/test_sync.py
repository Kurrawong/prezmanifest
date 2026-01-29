import json
import shutil
from pathlib import Path

import httpx
import prezmanifest.utils
from kurra.sparql import query
from typer.testing import CliRunner

from prezmanifest.loader import load
from prezmanifest.syncer import sync, make_catalogue
from prezmanifest.utils import artifact_file_name_from_graph_id
from rdflib import URIRef, RDF, SDO, Graph
from rdflib.compare import isomorphic

import datetime
runner = CliRunner()
from prezmanifest.cli import app


def test_sync(sparql_endpoint):
    MANIFEST_FILE_LOCAL = Path(__file__).parent / "local/manifest.ttl"
    MANIFEST_FILE_REMOTE = Path(__file__).parent / "remote/manifest.ttl"
    MANIFEST_ROOT = Path(__file__).parent / "local"

    # make copies of files that will be overwritten
    shutil.copy(MANIFEST_FILE_LOCAL, MANIFEST_FILE_LOCAL.with_suffix(".ttx"))
    shutil.copy(MANIFEST_ROOT / "catalogue.ttl", MANIFEST_ROOT / "catalogue.ttx")
    shutil.copy(MANIFEST_ROOT / "artifact6.ttl", MANIFEST_ROOT / "artifact6.ttx")

    # ensure the SPARQL store's clear
    query(sparql_endpoint, "DROP ALL")

    # load it with remote data
    load(MANIFEST_FILE_REMOTE, sparql_endpoint)

    a = sync(
        MANIFEST_FILE_LOCAL,
        sparql_endpoint,
    )

    # check status before sync
    assert a[str(MANIFEST_ROOT / "artifacts/artifact1.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact2.ttl")]["direction"] == "upload"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact3.ttl")]["direction"] == "upload"
    assert a[str(MANIFEST_ROOT / "artifact4.ttl")]["direction"] == "upload"
    assert a[str(MANIFEST_ROOT / "artifact5.ttl")]["direction"] == "add-remotely"
    assert a[str(MANIFEST_ROOT / "artifact6.ttl")]["direction"] == "download"
    assert a[str(MANIFEST_ROOT / "artifact7.ttl")]["direction"] == "upload"
    assert a["http://example.com/dataset/8"]["direction"] == "add-locally"
    assert a[str(MANIFEST_ROOT / "catalogue.ttl")]["direction"] == "same"

    # run sync again, performing no actions to just get updated status
    a = sync(
        MANIFEST_FILE_LOCAL, sparql_endpoint, httpx.Client(), False, False, False, False
    )

    # check status after sync
    assert a[str(MANIFEST_ROOT / "artifacts/artifact1.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact2.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact3.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact4.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact5.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact6.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact7.ttl")]["direction"] == "same"
    assert (
        a[
            str(
                MANIFEST_ROOT
                / artifact_file_name_from_graph_id("http://example.com/dataset/8")
            )
        ]["direction"]
        == "same"
    )
    assert a[str(MANIFEST_ROOT / "catalogue.ttl")]["direction"] == "same"

    # tidy up
    shutil.move(MANIFEST_ROOT / "manifest.ttx", MANIFEST_FILE_LOCAL)
    shutil.move(MANIFEST_ROOT / "catalogue.ttx", MANIFEST_ROOT / "catalogue.ttl")
    shutil.move(MANIFEST_ROOT / "artifact6.ttx", MANIFEST_ROOT / "artifact6.ttl")
    for f in MANIFEST_ROOT.glob("http--*.ttl"):
        f.unlink()


def test_sync_cli(sparql_endpoint):
    MANIFEST_FILE_REMOTE = Path(__file__).parent / "remote/manifest.ttl"

    # ensure the SPARQL store's clear
    query(sparql_endpoint, "DROP ALL")

    raw_output = str(
        runner.invoke(
            app, ["sync", str(MANIFEST_FILE_REMOTE), sparql_endpoint, "-f", "json"]
        ).output
    )

    r = json.loads(raw_output)

    assert str(MANIFEST_FILE_REMOTE.parent / "catalogue.ttl") in r.keys()

    # test cli pretty formatting
    raw_output = str(
        runner.invoke(app, ["sync", str(MANIFEST_FILE_REMOTE), sparql_endpoint]).stdout
    )
    assert "Main Entity" in raw_output


def test_sync_sync_predicate(sparql_endpoint):
    MANIFEST_FILE_LOCAL = Path(__file__).parent / "local/manifest-sync-pred.ttl"
    MANIFEST_FILE_REMOTE = Path(__file__).parent / "remote/manifest.ttl"
    MANIFEST_ROOT = Path(__file__).parent / "local"

    # make copies of files that will be overwritten
    shutil.copy(MANIFEST_FILE_LOCAL, MANIFEST_FILE_LOCAL.with_suffix(".ttx"))
    shutil.copy(MANIFEST_ROOT / "catalogue.ttl", MANIFEST_ROOT / "catalogue.ttx")
    shutil.copy(MANIFEST_ROOT / "artifact6.ttl", MANIFEST_ROOT / "artifact6.ttx")

    # ensure the SPARQL store's clear
    query(sparql_endpoint, "DROP ALL")

    # load it with remote data
    load(MANIFEST_FILE_REMOTE, sparql_endpoint)

    a = sync(
        MANIFEST_FILE_LOCAL,
        sparql_endpoint,
    )

    # check status before sync
    assert a[str(MANIFEST_ROOT / "artifacts/artifact1.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact2.ttl")]["direction"] == "upload"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact3.ttl")]["direction"] == "upload"
    assert a[str(MANIFEST_ROOT / "artifact4.ttl")]["direction"] == "upload"
    assert a[str(MANIFEST_ROOT / "artifact5.ttl")]["direction"] == "add-remotely"
    assert a[str(MANIFEST_ROOT / "artifact6.ttl")]["direction"] == "download"
    assert a[str(MANIFEST_ROOT / "artifact7.ttl")]["direction"] == "upload"
    assert a["http://example.com/dataset/8"]["direction"] == "add-locally"
    assert a[str(MANIFEST_ROOT / "catalogue.ttl")]["direction"] == "same"

    # run sync again, performing no actions to just get updated status
    a = sync(
        MANIFEST_FILE_LOCAL, sparql_endpoint, httpx.Client(), False, False, False, False
    )

    # check status after sync
    assert a[str(MANIFEST_ROOT / "artifacts/artifact1.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact2.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifacts/artifact3.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact4.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact5.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact6.ttl")]["direction"] == "same"
    assert a[str(MANIFEST_ROOT / "artifact7.ttl")]["direction"] == "same"
    assert (
        a[
            str(
                MANIFEST_ROOT
                / artifact_file_name_from_graph_id("http://example.com/dataset/8")
            )
        ]["direction"]
        == "same"
    )
    assert a[str(MANIFEST_ROOT / "catalogue.ttl")]["direction"] == "same"

    # tidy up
    shutil.move(MANIFEST_ROOT / "manifest-sync-pred.ttx", MANIFEST_FILE_LOCAL)
    shutil.move(MANIFEST_ROOT / "catalogue.ttx", MANIFEST_ROOT / "catalogue.ttl")
    shutil.move(MANIFEST_ROOT / "artifact6.ttx", MANIFEST_ROOT / "artifact6.ttl")
    for f in MANIFEST_ROOT.glob("http--*.ttl"):
        f.unlink()


def test_make_catalogue():
    MANIFEST_FILE_LOCAL = Path(__file__).parent / "local/manifest.ttl"
    c = make_catalogue(MANIFEST_FILE_LOCAL, reuse_cat_iri=False, new_cat_iri="http://example.com/cat/x")
    assert (URIRef("http://example.com/cat/x"), RDF.type, SDO.DataCatalog) in c

    c = make_catalogue(MANIFEST_FILE_LOCAL, reuse_cat_iri=True)
    assert (URIRef("https://example.com/sync-test"), RDF.type, SDO.DataCatalog) in c


def test_make_catalogue_manifest_additions():
    original = """PREFIX prof: <http://www.w3.org/ns/dx/prof/>
PREFIX schema: <https://schema.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

[]    a <https://prez.dev/Manifest> ;
    prof:hasResource
        [
            prof:hasArtifact
                "local/artifacts/*.ttl" ,
                "local/artifact4.ttl" ,
                "local/artifact5.ttl" ,
                "local/artifact6.ttl" ,
                [
                    schema:contentLocation "local/artifact7.ttl" ;
                    schema:mainEntity <http://example.com/dataset/7> ;
                ] ,
                [
                    schema:contentLocation "local/artifact9.ttl" ;
                    schema:dateModified "2025-03-02"^^xsd:date ;
                    schema:mainEntity <http://example.com/dataset/9> ;
                ] ;
            prof:hasRole <https://prez.dev/ManifestResourceRoles/ResourceData> ;
        ] ;
."""

    target = prezmanifest.utils.load_graph(
        """
        PREFIX prof: <http://www.w3.org/ns/dx/prof/>
        PREFIX schema: <https://schema.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        []    a <https://prez.dev/Manifest> ;
            prof:hasResource 
                [
                    prof:hasArtifact
                        "local/artifacts/*.ttl" ,
                        "local/artifact4.ttl" ,
                        "local/artifact5.ttl" ,
                        "local/artifact6.ttl" ,
                        [
                            schema:contentLocation "local/artifact7.ttl" ;
                            schema:mainEntity <http://example.com/dataset/7> ;
                        ] ,
                        [
                            schema:contentLocation "local/artifact9.ttl" ;
                            schema:dateModified "2025-03-02"^^xsd:date ;
                            schema:mainEntity <http://example.com/dataset/9> ;
                        ] ;
                    prof:hasRole <https://prez.dev/ManifestResourceRoles/ResourceData> ;
                ] ,
                [
                    prof:hasArtifact "catalogue.ttl" ;
                    prof:hasRole <https://prez.dev/ManifestResourceRoles/CatalogueData> ;
                ] ;
        .""")

    make_catalogue(Path(__file__).parent / "manifest-nocat.ttl", new_cat_iri="http://example.com/cat/y")

    actual = prezmanifest.utils.load_graph(Path(__file__).parent / "manifest-nocat.ttl")

    assert isomorphic(actual, target)

    # cleanup
    Path(Path(__file__).parent / "catalogue.ttl").unlink(missing_ok=True)
    with open(Path(__file__).parent / "manifest-nocat.ttl", "w") as f:
        f.write(original)


def test_make_catalogue_new_iri():
    original = prezmanifest.utils.load_graph(
        """
        PREFIX schema: <https://schema.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        <http://example.com/cat/x>
            a schema:DataCatalog ;
            schema:dateModified "{XXX}"^^xsd:date ;
            schema:hasPart
                <http://example.com/dataset/1> ,
                <http://example.com/dataset/2> ,
                <http://example.com/dataset/3> ;
        .
        """.replace("{XXX}", datetime.datetime.now().isoformat()[:10]))

    original.serialize(format="longturtle", destination=Path(__file__).parent / "catalogue.2.ttl")

    target = prezmanifest.utils.load_graph(
        """
        PREFIX schema: <https://schema.org/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        <http://example.com/cat/y>
            a schema:DataCatalog ;
            schema:dateModified "{XXX}"^^xsd:date ;
            schema:hasPart
                <http://example.com/dataset/1> ,
                <http://example.com/dataset/2> ,
                <http://example.com/dataset/3> ,
                <http://example.com/dataset/4> ,
                <http://example.com/dataset/5> ,
                <http://example.com/dataset/6> ,
                <http://example.com/dataset/7> ,
                <http://example.com/dataset/9> ;
        .
        """.replace("{XXX}", datetime.datetime.now().isoformat()[:10]))

    actual = make_catalogue(Path(__file__).parent / "manifest-cat.ttl", new_cat_iri="http://example.com/cat/y")

    assert isomorphic(actual, target)

    # cleanup
    Path(Path(__file__).parent / "catalogue.2.ttl").unlink(missing_ok=True)

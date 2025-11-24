import io
import time

import httpx
from rdflib.query import Result
from typer.testing import CliRunner

from prezmanifest.cli import app

runner = CliRunner()


def test_sync_rdf_delta(sparql_endpoint: str, delta_url: str, datasource: str):
    result = runner.invoke(
        app,
        [
            "event",
            "sync",
            "rdf-delta",
            "tests/demo-vocabs/manifest-mainEntity.ttl",
            sparql_endpoint,
            delta_url,
            datasource,
        ],
    )
    if result.exception is not None:
        raise result.exception
    assert result.exit_code == 0
    assert "successfully synchronized" in result.output

    query = """
                PREFIX olis: <https://olis.dev/>
                PREFIX schema: <https://schema.org/>
                PREFIX mvt: <https://prez.dev/ManifestVersionTypes/>
                ASK {
                    GRAPH olis:SystemGraph {
                        <https://example.com/demo-vocabs> a olis:VirtualGraph ;
                            schema:version [
                                schema:additionalType mvt:GitCommitHash ;
                            ]
                    } 
                }
            """
    headers = {
        "Content-Type": "application/sparql-query",
        "Accept": "application/sparql-results+json",
    }
    time.sleep(0.5)
    response = httpx.post(sparql_endpoint, headers=headers, content=query)
    response.raise_for_status()
    result = Result.parse(
        io.BytesIO(response.content), response.headers["Content-Type"].split(";")[0]
    )
    assert result.askAnswer

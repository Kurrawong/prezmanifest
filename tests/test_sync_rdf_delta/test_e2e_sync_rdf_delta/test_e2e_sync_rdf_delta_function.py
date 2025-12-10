import io
import time
from pathlib import Path

import httpx
from rdflib.query import Result

from prezmanifest.event.client import DeltaEventClient
from prezmanifest.event.syncer import sync_rdf_delta


def test(client: DeltaEventClient, sparql_endpoint: str):
    """
    This tests a sync where the previous commit is not found and loads the manifest with only append statements in
    the RDF patch log.
    """
    project_root = Path(__file__).parent.parent.parent.parent
    manifest_path = (
        Path(__file__).parent.parent.parent / "demo-vocabs/manifest-mainEntity.ttl"
    )
    assert manifest_path.exists()
    with httpx.Client() as http_client:
        sync_rdf_delta(
            project_root,
            manifest_path,
            sparql_endpoint=sparql_endpoint,
            http_client=http_client,
            event_client=client,
        )

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

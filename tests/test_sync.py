from pathlib import Path

from prezmanifest.syncer import sync


def test_sync():
    SPARQL_ENDPOINT = "http://localhost:3030/test/"
    MANIFEST_FILE = Path(__file__).parent / "demo-vocabs-updated1/manifest.ttl"
    r = sync(MANIFEST_FILE, SPARQL_ENDPOINT)
    print(r)

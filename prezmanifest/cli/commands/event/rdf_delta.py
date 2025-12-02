from pathlib import Path
from typing import Annotated

import typer

from prezmanifest.event.client import DeltaEventClient
from prezmanifest.event.syncer import sync_rdf_delta
from prezmanifest.utils import make_httpx_client

app = typer.Typer()


@app.command(
    name="rdf-delta",
    help="Synchronize a Prez Manifest's resources by sending RDF patch logs to RDF Delta.",
)
def event_sync_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be loaded"
    ),
    endpoint: str = typer.Argument(..., help="The URL of the SPARQL Endpoint"),
    delta_url: str = typer.Argument(..., help="The URL of the RDF Delta endpoint"),
    delta_datasource: str = typer.Argument(
        ..., help="The name of the RDF Delta datasource"
    ),
    username: Annotated[
        str, typer.Option("--username", "-u", help="SPARQL Endpoint username")
    ] = None,
    password: Annotated[
        str, typer.Option("--password", "-p", help="SPARQL Endpoint password")
    ] = None,
    timeout: Annotated[
        int, typer.Option("--timeout", "-t", help="Timeout per request")
    ] = 60,
):
    cwd = Path.cwd()
    http_client = make_httpx_client(username, password, timeout)
    event_client = DeltaEventClient(delta_url, delta_datasource)
    try:
        sync_rdf_delta(cwd, manifest, endpoint, http_client, event_client)
        print("The Prez Manifest synchronization event has been sent to RDF Delta.")
    finally:
        http_client.close()

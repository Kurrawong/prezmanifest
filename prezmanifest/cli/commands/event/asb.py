from pathlib import Path
from typing import Annotated

import typer

from prezmanifest.event.asb_client import AzureServiceBusEventClient
from prezmanifest.event.syncer import sync_rdf_delta
from prezmanifest.utils import make_httpx_client

app = typer.Typer()


@app.command(
    name="azure-service-bus",
    help="Synchronize a Prez Manifest's resources by sending RDF patch logs to Azure Service Bus.",
)
def event_sync_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be loaded"
    ),
    endpoint: str = typer.Argument(..., help="The URL of the SPARQL Endpoint"),
    connection: str = typer.Argument(
        ..., help="The Azure Service Bus connection string"
    ),
    topic: str = typer.Argument(..., help="The Azure Service Bus topic name"),
    subscription: str = typer.Argument(
        ..., help="The Azure Service Bus subscription name"
    ),
    session: str = typer.Argument(..., help="The Azure Service Bus session ID"),
    websocket: bool = typer.Option(False, "--websocket", help="Use WebSockets"),
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
    event_client = AzureServiceBusEventClient(
        connection, topic, subscription, session, websocket
    )
    try:
        sync_rdf_delta(cwd, manifest, endpoint, http_client, event_client)
        print(
            "The Prez Manifest synchronization event has been sent to Azure Service Bus."
        )
    finally:
        http_client.close()

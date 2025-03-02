from pathlib import Path
from typing import Annotated

import typer

from prezmanifest.cli.app import app
from prezmanifest.syncer import sync


@app.command(
    name="sync",
    help="Synchronize a Prez Manifest's resources with loaded copies of them in a SPARQL Endpoint",
)
def sync_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be loaded"
    ),
    endpoint: str = typer.Argument(..., help="The URL of the SPARQL Endpoint"),
    username: Annotated[
        str, typer.Option("--username", "-u", help="SPARQL Endpoint username")
    ] = None,
    password: Annotated[
        str, typer.Option("--password", "-p", help="SPARQL Endpoint password")
    ] = None,
) -> None:
    sync(
        manifest,
        sparql_endpoint=endpoint,
        sparql_username=username,
        sparql_password=password,
    )

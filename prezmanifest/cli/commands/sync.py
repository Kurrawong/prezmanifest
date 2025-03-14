from pathlib import Path
from typing import Annotated

import typer

from prezmanifest.cli.app import app
from prezmanifest.syncer import sync
from prezmanifest.utils import make_httpx_client


@app.command(
    name="sync",
    help="Synchronize a Prez Manifest's resources with loaded copies of them in a SPARQL Endpoint",
)
def sync_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be loaded"
    ),
    endpoint: str = typer.Argument(..., help="The URL of the SPARQL Endpoint"),
    update_remote: bool = typer.Argument(True, help="Copy more recent local artifacts to DB"),
    update_local: bool = typer.Argument(True, help="Copy more recent DB artifacts to local"),
    add_remote: bool = typer.Argument(True, help="Add new local artifacts to DB"),
    add_local: bool = typer.Argument(True, help="Add new DB artifacts to local"),
    username: Annotated[
        str, typer.Option("--username", "-u", help="SPARQL Endpoint username")
    ] = None,
    password: Annotated[
        str, typer.Option("--password", "-p", help="SPARQL Endpoint password")
    ] = None,
) -> None:
    print(sync(
        manifest,
        endpoint,
        make_httpx_client(username, password),
        update_remote,
        update_local,
        add_remote,
        add_local
    ))

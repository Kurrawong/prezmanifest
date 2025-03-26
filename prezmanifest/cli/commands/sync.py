import collections
import json
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from prezmanifest.cli.app import app
from prezmanifest.cli.console import console
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
    update_remote: bool = typer.Argument(
        True, help="Copy more recent local artifacts to DB"
    ),
    update_local: bool = typer.Argument(
        True, help="Copy more recent DB artifacts to local"
    ),
    add_remote: bool = typer.Argument(True, help="Add new local artifacts to DB"),
    add_local: bool = typer.Argument(True, help="Add new DB artifacts to local"),
    username: Annotated[
        str, typer.Option("--username", "-u", help="SPARQL Endpoint username")
    ] = None,
    password: Annotated[
        str, typer.Option("--password", "-p", help="SPARQL Endpoint password")
    ] = None,
    response_format: str = typer.Option(
        "table",
        "--response-format",
        "-f",
        help="The response format of the SPARQL query. Either 'table' (default) or 'json'",
    ),
) -> None:
    r = sync(
        manifest,
        endpoint,
        make_httpx_client(username, password),
        update_remote,
        update_local,
        add_remote,
        add_local,
    )

    if response_format == "json":
        print(json.dumps(r, indent=4))
    else:
        console.print(result_as_rich_table(r))


def result_as_rich_table(sync_status: dict):
    t = Table()
    t.add_column("Artifact")
    t.add_column("Main Entity")
    t.add_column("Direction")

    for k, v in collections.OrderedDict(sorted(sync_status.items())).items():
        t.add_row(str(k), str(v["main_entity"]), v["direction"])

    # json.dumps(sync_status, indent=4)

    return t

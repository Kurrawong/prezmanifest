from tokenize import endpats

import typer
from rich.progress import track
from typing import Annotated
from pathlib import Path
from prezmanifest.cli.console import console


app = typer.Typer(help="Prez Manifest load commands")


@app.command(name="sparql", help="Load a Prez Manifest's resources into a SPARQL Endpoint")
def load_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be loaded"
    ),
    endpoint: Path = typer.Argument(
        ..., help="The URL of the SPARQL Endpoint"
    ),
    username: Annotated[
        str, typer.Option("--username", "-u", help="SPARQL Endpoint username.")
    ] = None,
    password: Annotated[
        str, typer.Option("--password", "-p", help="SPARQL Endpoint password.")
    ] = None,
) -> None:
    o = f"Loaded the manifest at {manifest} into the SPARQL Endpoint {endpoint}"
    if username is not None or password is not None:
        o += f" with {username} and {password}"
    console.print(o)


@app.command(name="file", help="Load a Prez Manifest's resources into a single RDF quads file")
def load_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be loaded"
    ),
    file: Path = typer.Argument(
        ..., help="The path of the quads filet"
    ),
) -> None:
    console.print(f"Loaded the manifest at {manifest} into the file {file}")
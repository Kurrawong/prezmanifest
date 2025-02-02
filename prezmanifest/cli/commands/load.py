from pathlib import Path
from typing import Annotated

import typer

from prezmanifest.loader import load

app = typer.Typer(help="Load a Prez Manifest's content into a file or DB")


@app.command(
    name="sparql", help="Load a Prez Manifest's resources into a SPARQL Endpoint"
)
def sparql_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be loaded"
    ),
    endpoint: str = typer.Argument(..., help="The URL of the SPARQL Endpoint"),
    username: Annotated[
        str, typer.Option("--username", "-u", help="SPARQL Endpoint username.")
    ] = None,
    password: Annotated[
        str, typer.Option("--password", "-p", help="SPARQL Endpoint password.")
    ] = None,
) -> None:
    load(
        manifest,
        sparql_endpoint=endpoint,
        sparql_username=username,
        sparql_password=password,
    )


@app.command(
    name="file", help="Load a Prez Manifest's resources into a single RDF quads file"
)
def file_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be loaded"
    ),
    file: Path = typer.Argument(..., help="The path of the quads file"),
) -> None:
    load(manifest, destination_file=file)

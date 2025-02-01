import typer
from rich.progress import track
from pathlib import Path
from prezmanifest.cli.console import console
from enum import Enum

class TableFormats(str, Enum):
    asciidoc = "asciidoc"
    markdown = "markdown"


app = typer.Typer(help="Prez Manifest document commands")



@app.command(name="table", help="Create a Markdown or ASCIIDOC table for the resources listed in a Prez Manifest")
def table_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be documented"
    ),
    table_format: TableFormats = typer.Option(
        TableFormats.markdown,
        "--format",
        "-f",
        help="The format of the table to be created",
    ),
) -> None:
    console.print(f"Created a table for the Manifest at {manifest} in the {format} format")


@app.command(name="catalogue", help="Add the resources listed in a Prez Manifest to a catalogue RDF file")
def catalogue_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be documented"
    ),
) -> None:
    console.print(f"Created a table for the Manifest at {manifest}")

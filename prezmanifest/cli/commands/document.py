from pathlib import Path

import typer

from prezmanifest.documentor import TableFormats, catalogue, table

app = typer.Typer(help="Create documentation from a Prez Manifest")


@app.command(
    name="table",
    help="Create a Markdown or ASCIIDOC table for the resources listed in a Prez Manifest",
)
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
    print(table(manifest, table_format))


@app.command(
    name="catalogue",
    help="Add the resources listed in a Prez Manifest to a catalogue RDF file",
)
def catalogue_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be documented"
    ),
) -> None:
    print(catalogue(manifest).serialize(format="longturtle"))

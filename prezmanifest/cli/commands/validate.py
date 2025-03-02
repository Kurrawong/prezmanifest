from pathlib import Path

import typer

from prezmanifest.cli.app import app
from prezmanifest.validator import validate


@app.command(
    name="validate", help="Validate the structure and content of a Prez Manifest"
)
def validate_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be validated"
    ),
) -> None:
    validate(manifest)

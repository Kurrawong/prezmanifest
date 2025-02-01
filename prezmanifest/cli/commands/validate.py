from pathlib import Path

import typer

from prezmanifest.cli.console import console

app = typer.Typer(help="Prez Manifest validate commands")


@app.command(name="validate", help="Validate a Prez Manifest")
def validate_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be validated"
    ),
) -> None:
    console.print(f"Validated the Manifest at {manifest}")

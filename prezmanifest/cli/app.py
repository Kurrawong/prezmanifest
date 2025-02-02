from typing import Annotated

import typer

from prezmanifest import __version__
from prezmanifest.cli.console import console

app = typer.Typer(
    invoke_without_command=True,
    context_settings={
        "help_option_names": ["-h", "--help"],
    },
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[bool, typer.Option("--version", "-v", is_eager=True)] = False,
):
    """PrezManifest top-level Command Line Interface. Ask for help (-h) for each Command"""
    if version:
        console.print(__version__)
        raise typer.Exit()

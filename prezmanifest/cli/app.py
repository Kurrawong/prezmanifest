import logging
import os
import sys
from typing import Annotated

import typer

from prezmanifest import __version__
from prezmanifest.cli.console import console


# Configure logging
def setup_logging():
    """Set up logging configuration for the CLI."""
    # Get log level from environment or default to WARNING
    log_level_str = os.getenv("PM_LOG_LEVEL", "WARNING").upper()
    log_level = getattr(logging, log_level_str, logging.WARNING)

    # Create logger
    logger = logging.getLogger("prezmanifest")
    logger.setLevel(log_level)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)


# Set up logging when the module is imported
setup_logging()

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

import typer
from rich.progress import track
from pathlib import Path
from prezmanifest.cli.console import console


app = typer.Typer(help="Prez Manifest label commands")


@app.command(name="iris", help="Find all the IRIs of objects in the Manifest's resources without labels")
def iris_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be labelled"
    ),
) -> None:
    console.print(f"Labelled the Manifest at {manifest}")


@app.command(name="rdf", help="Create labels for all the objects in the Manifest's resources without labels")
def rdf_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be labelled"
    ),
    context: Path = typer.Argument(
        ..., help="The path of an RDF file, a directory of RDF files or the URL of a SPARQL endpoint from which t obtain labels"
    ),
) -> None:
    console.print(f"Labels obtained for {manifest} from {context}")


@app.command(name="manifest", help="Create labels for all the objects in the Manifest's resources without labels and store them as a new Manifest resource")
def manifest_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be labelled"
    ),
    context: Path = typer.Argument(
        ...,
        help="The path of an RDF file, a directory of RDF files or the URL of a SPARQL endpoint from which t obtain labels"
    ),
) -> None:
    console.print(f"Labels obtained for {manifest} from {context} have been added back into the Manifest")

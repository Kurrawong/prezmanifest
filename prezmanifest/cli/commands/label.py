from pathlib import Path
from typing import Annotated

import typer

from prezmanifest.labeller import LabellerOutputTypes, label
from prezmanifest.utils import make_httpx_client

app = typer.Typer(
    help="Discover labels missing from data in a in a Prez Manifest and patch them"
)


@app.command(
    name="iris",
    help="Find all the IRIs of objects in the Manifest's resources without labels",
)
def iris_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be labelled"
    ),
    context: str = typer.Argument(
        None,
        help="The path of an RDF file, a directory of RDF files or the URL of a SPARQL endpoint from which to obtain labels",
    ),
    username: Annotated[
        str, typer.Option("--username", "-u", help="SPARQL Endpoint username")
    ] = None,
    password: Annotated[
        str, typer.Option("--password", "-p", help="SPARQL Endpoint password")
    ] = None,
) -> None:
    for iri in label(
        manifest,
        LabellerOutputTypes.iris,
        context,
        make_httpx_client(username, password),
    ):
        print(str(iri))


@app.command(
    name="rdf",
    help="Create labels for all the objects in the Manifest's resources without labels",
)
def rdf_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be labelled"
    ),
    context: str = typer.Argument(
        None,
        help="The path of an RDF file, a directory of RDF files or the URL of a SPARQL endpoint from which to obtain labels",
    ),
    username: Annotated[
        str, typer.Option("--username", "-u", help="SPARQL Endpoint username")
    ] = None,
    password: Annotated[
        str, typer.Option("--password", "-p", help="SPARQL Endpoint password")
    ] = None,
) -> None:
    print(
        label(
            manifest,
            LabellerOutputTypes.rdf,
            context,
            make_httpx_client(username, password),
        ).serialize(format="longturtle")
    )


@app.command(
    name="manifest",
    help="Create labels for all the objects in the Manifest's resources without labels and store them as a new Manifest resource",
)
def manifest_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be labelled"
    ),
    context: Path = typer.Argument(
        ...,
        help="The path of an RDF file, a directory of RDF files or the URL of a SPARQL endpoint from which to obtain labels",
    ),
    username: Annotated[
        str, typer.Option("--username", "-u", help="SPARQL Endpoint username")
    ] = None,
    password: Annotated[
        str, typer.Option("--password", "-p", help="SPARQL Endpoint password")
    ] = None,
) -> None:
    label(
        manifest,
        LabellerOutputTypes.manifest,
        context,
        make_httpx_client(username, password),
    )

    print("A new Resource containing labels has been added to the Manifest")

from pathlib import Path

import typer

from prezmanifest.labeller import LabellerOutputTypes, label

app = typer.Typer(help="Discover labels missing from data in a in a Prez Manifest and patch them")


@app.command(
    name="iris",
    help="Find all the IRIs of objects in the Manifest's resources without labels",
)
def iris_command(
    manifest: Path = typer.Argument(
        ..., help="The path of the Prez Manifest file to be labelled"
    ),
) -> None:
    for iri in label(manifest, LabellerOutputTypes.iris):
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
        help="The path of an RDF file, a directory of RDF files or the URL of a SPARQL endpoint from which t obtain labels",
    ),
) -> None:
    print(
        label(manifest, LabellerOutputTypes.rdf, context).serialize(format="longturtle")
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
        help="The path of an RDF file, a directory of RDF files or the URL of a SPARQL endpoint from which t obtain labels",
    ),
) -> None:
    label(manifest, additional_context=context)

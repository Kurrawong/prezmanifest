from prezmanifest.cli.app import app
from prezmanifest.cli.commands.document import app as document_app
from prezmanifest.cli.commands.label import app as label_app
from prezmanifest.cli.commands.load import app as load_app
from prezmanifest.cli.commands.validate import validate_command
from prezmanifest.cli.commands.sync import sync_command

app.add_typer(label_app, name="label")
app.add_typer(document_app, name="document")
app.add_typer(load_app, name="load")
# app.add_typer(validate_command)

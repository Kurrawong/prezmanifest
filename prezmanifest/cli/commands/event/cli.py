import typer

from prezmanifest.cli.commands.event.rdf_delta import app as rdf_delta_app

event_app = typer.Typer(name="event", help="Event-based Prez Manifests actions")
sync_app = typer.Typer()
event_app.add_typer(
    sync_app, name="sync", help="Synchronize a Prez Manifest with an event system"
)
sync_app.add_typer(rdf_delta_app)

try:
    import azure.servicebus

    from prezmanifest.cli.commands.event.asb import app as asb_app

    sync_app.add_typer(asb_app)
except ImportError:
    pass

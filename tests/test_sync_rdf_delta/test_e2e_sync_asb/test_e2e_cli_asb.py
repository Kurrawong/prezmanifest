import time
from pathlib import Path
from unittest.mock import patch

from azure.servicebus import ServiceBusClient
from typer.testing import CliRunner

from prezmanifest.cli import app
from prezmanifest.event.asb_client import AzureServiceBusEventClient

runner = CliRunner()

manifest_file = str(
    Path(__file__).parent.parent.parent / "demo-vocabs/manifest-mainEntity.ttl"
)


def test_sync_azure_service_bus(
    sparql_endpoint: str,
    connection_string: str,
    topic: str,
    subscription: str,
    session: str,
):
    # Capture the rdf_patch_body passed to event_client.create_event
    captured_rdf_patch_body = None

    original_create_event = AzureServiceBusEventClient.create_event

    def spy_create_event(self, payload: str) -> None:
        nonlocal captured_rdf_patch_body
        captured_rdf_patch_body = payload
        return original_create_event(self, payload)

    with patch(
        "prezmanifest.event.asb_client.AzureServiceBusEventClient.create_event",
        spy_create_event,
    ):
        result = runner.invoke(
            app,
            [
                "event",
                "sync",
                "azure-service-bus",
                manifest_file,
                sparql_endpoint,
                connection_string,
                topic,
                subscription,
                session,
            ],
        )
        if result.exception is not None:
            raise result.exception
        assert result.exit_code == 0
        assert (
            "The Prez Manifest synchronization event has been sent to Azure Service Bus."
            in result.output
        )

    # Check that the event was sent to the Azure Service Bus
    servicebus_client = ServiceBusClient.from_connection_string(connection_string)
    try:
        receiver = servicebus_client.get_subscription_receiver(
            topic_name=topic, subscription_name=subscription, session_id=session
        )
        try:
            time.sleep(1)
            received_messages = receiver.receive_messages(
                max_message_count=1, max_wait_time=5
            )
            assert len(received_messages) > 0, (
                "No message received from Azure Service Bus"
            )

            # Verify the message has the expected content type
            message = received_messages[0]
            assert message.content_type == "application/rdf-patch-body"
            assert message.session_id == session
            body = b"".join(message.body).decode("utf-8")
            assert len(body) > 0
            assert "TX ." in body

            # Compare the received body with the captured rdf_patch_body
            assert captured_rdf_patch_body is not None
            assert body == captured_rdf_patch_body

            receiver.complete_message(message)
        finally:
            receiver.close()
    finally:
        servicebus_client.close()

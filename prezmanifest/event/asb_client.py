import datetime

from azure.servicebus import ServiceBusClient, ServiceBusMessage, TransportType
from rdflib import SDO


class AzureServiceBusEventClient:
    def __init__(
        self,
        connection_string: str,
        topic: str,
        subscription: str,
        session_id: str,
        websocket: bool = False,
    ):
        self.topic = topic
        self.subscription = subscription
        self.session_id = session_id
        kwargs = (
            {} if not websocket else {"transport_type": TransportType.AmqpOverWebsocket}
        )
        self._inner = ServiceBusClient.from_connection_string(
            connection_string, **kwargs
        )

    def create_event(self, payload: str) -> None:
        content_type = "application/rdf-patch-body"
        metadata = {
            str(SDO.encodingFormat): content_type,
            str(SDO.dateCreated): datetime.datetime.now(datetime.UTC).strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
            str(SDO.schemaVersion): None,
            str(SDO.about): "",
            str(SDO.creator): "prezmanifest",
        }
        _message = ServiceBusMessage(
            payload,
            content_type=content_type,
            application_properties=metadata,
            session_id=self.session_id,
        )
        sender = self._inner.get_topic_sender(self.topic)
        sender.send_messages(message=_message)
        sender.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._inner.close()

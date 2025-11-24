import datetime
from typing import Protocol
from uuid import uuid4

from azure.servicebus import ServiceBusClient, ServiceBusMessage, TransportType
from rdf_delta import DeltaClient
from rdflib import SDO


class EventClient(Protocol):
    def create_event(self, payload: str) -> None: ...


class DeltaEventClient:
    def __init__(self, url: str, datasource: str) -> None:
        self._inner = DeltaClient(url)
        self.datasource = datasource

    def _add_patch_log_header(self, patch_log: str) -> str:
        ds = self._inner.describe_datasource(self.datasource)
        ds_log = self._inner.describe_log(ds.id)
        previous_id = ds_log.latest
        new_id = str(uuid4())
        if previous_id:
            modified_patch_log = (
                f"""
                    H id <uuid:{new_id}> .
                    H prev <uuid:{previous_id}> .
                """
                + patch_log
            )
        else:
            modified_patch_log = (
                f"""
                H id <uuid:{new_id}> .
            """
                + patch_log
            )
        return modified_patch_log

    def create_event(self, payload: str) -> None:
        patch_log = self._add_patch_log_header(payload)
        self._inner.create_log(patch_log, self.datasource)


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

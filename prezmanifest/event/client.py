from typing import Protocol
from uuid import uuid4

from rdf_delta import DeltaClient


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

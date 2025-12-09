# tests/test_awsscript_memorysetup.py

from typing import Any, Dict

import awsscript.memorysetup


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg: str, *args, **kwargs):
        self.messages.append(msg)


def test_create_memory_resource_calls_memory_client(monkeypatch):
    """create_memory_resource should call MemoryClient.create_memory_and_wait with correct args."""
    calls: Dict[str, Any] = {}

    class FakeMemoryClient:
        def create_memory_and_wait(self, name, description, strategies, event_expiry_days):
            calls["name"] = name
            calls["description"] = description
            calls["strategies"] = strategies
            calls["event_expiry_days"] = event_expiry_days
            return {"memoryId": "mem-123"}

    monkeypatch.setattr(awsscript.memorysetup, "memory_client", FakeMemoryClient(), raising=False)
    awsscript.memorysetup.logger = DummyLogger()

    awsscript.memorysetup.create_memory_resource()

    assert calls["name"] == awsscript.memorysetup.memory_name
    assert calls["description"] == "Gap Exeption Memory"
    assert calls["event_expiry_days"] == 90
    assert isinstance(calls["strategies"], list)
    assert len(calls["strategies"]) == 2

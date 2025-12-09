# tests/test_awsscript_invokeagent.py

import importlib
from io import BytesIO

import pytest


def test_awsscript_invokeagent_parses_output(monkeypatch, capsys):
    """On import, awsscript_invokeagent should invoke the agent runtime and print decoded chunks."""

    class FakeEvents:
        def __init__(self):
            self.registered = []

        def register_first(self, event_name, handler):
            self.registered.append((event_name, handler))
            return "handler-id"

        def unregister(self, event_name, handler_id):
            self.registered.append(("unregister", event_name, handler_id))

    class FakeClient:
        def __init__(self):
            self.meta = type("M", (), {"events": FakeEvents()})

        def invoke_agent_runtime(self, **kwargs):
            # Simulate Bedrock AgentCore streaming payload
            body = b'data: "Hello world"\\n\\n'
            return {"response": BytesIO(body)}

    def fake_boto3_client(service_name, region_name=None):
        assert service_name == "bedrock-agentcore"
        return FakeClient()

    import boto3
    monkeypatch.setattr(boto3, "client", fake_boto3_client, raising=False)

    # Import the script; it runs on import
    importlib.import_module("awsscript_invokeagent")

    captured = capsys.readouterr()
    assert "Hello world" in captured.out

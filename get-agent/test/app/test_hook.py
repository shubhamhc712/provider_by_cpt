# tests/test_app_hooks.py

from typing import Any, Dict

import pytest

from app.hook import RequestContextInjectingHook
from app.context import AgentRequestContext


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg: str, *args, **kwargs):
        self.messages.append(msg)


def test_request_context_injecting_hook_before_invocation(monkeypatch):
    """Hook should rebuild AgentRequestContext from agent.state and then call update_event()."""

    calls: Dict[str, Any] = {}

    original_init = AgentRequestContext.__init__
    original_update = AgentRequestContext.update_event

    def fake_init(self, **kwargs):
        calls["kwargs"] = kwargs

    def fake_update_event(self, event, logger):
        calls["updated"] = True

    monkeypatch.setattr(AgentRequestContext, "__init__", fake_init, raising=False)
    monkeypatch.setattr(AgentRequestContext, "update_event", fake_update_event, raising=False)

    class FakeState:
        def get(self):
            return {"lat": 10.0, "lang": 20.0, "plan": "Choice"}

    class FakeAgent:
        def __init__(self):
            self.state = FakeState()

    class FakeEvent:
        def __init__(self):
            self.agent = FakeAgent()

    hook = RequestContextInjectingHook(logger=DummyLogger())
    hook.before_invocation(FakeEvent())

    assert calls["kwargs"] == {"lat": 10.0, "lang": 20.0, "plan": "Choice"}
    assert calls["updated"] is True

    # restore (optional; pytest will clean anyway)
    monkeypatch.setattr(AgentRequestContext, "__init__", original_init, raising=False)
    monkeypatch.setattr(AgentRequestContext, "update_event", original_update, raising=False)


def test_request_context_injecting_hook_registers(monkeypatch):
    """register_hooks should register before_invocation for BeforeToolCallEvent."""

    class FakeRegistry:
        def __init__(self):
            self.callbacks = []

        def add_callback(self, event_type, callback):
            self.callbacks.append((event_type, callback))

    # We don't actually need real BeforeToolCallEvent, just that something is registered
    from strands import hooks as strands_hooks

    class FakeEventType:
        pass

    monkeypatch.setattr(strands_hooks, "BeforeToolCallEvent", FakeEventType, raising=False)

    registry = FakeRegistry()
    hook = RequestContextInjectingHook(logger=DummyLogger())

    hook.register_hooks(registry)

    assert len(registry.callbacks) == 1
    event_type, cb = registry.callbacks[0]
    assert event_type is FakeEventType
    assert callable(cb)

# tests/test_app_context.py

from typing import Any, Dict

from app.context import AgentRequestContext
from app.constants import HDR_LAT, HDR_LANG, HDR_PLAN


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg: str, *args, **kwargs):
        self.messages.append(msg)


def test_from_agent_core_context_reads_headers():
    """AgentRequestContext should pull lat/lang/plan from AgentCoreContext headers."""

    class FakeAgentCoreContext:
        def __init__(self):
            self._values = {
                HDR_LAT: 41.0,
                HDR_LANG: -87.0,
                HDR_PLAN: "Choice Plus",
            }

        def get_header_values(self, key):
            return self._values.get(key)

    src = FakeAgentCoreContext()
    ctx = AgentRequestContext.from_agent_core_context(src)

    assert ctx.lat == 41.0
    assert ctx.lang == -87.0
    assert ctx.plan == "Choice Plus"


def test_update_event_injects_lat_lang_plan():
    """update_event should inject lat, lang, plan into tool input if tool schema has those fields."""
    logger = DummyLogger()
    ctx = AgentRequestContext(lat=41.0, lang=-87.0, plan="Choice Plus")

    class FakeSelectedTool:
        def __init__(self):
            self.spec: Dict[str, Any] = {
                "inputSchema": {
                    "json": {
                        "properties": {
                            "lat": {"type": "number"},
                            "lang": {"type": "number"},
                            "plan": {"type": "string"},
                        }
                    }
                }
            }

    class FakeEvent:
        def __init__(self):
            self.selected_tool = FakeSelectedTool()
            self.tool_use: Dict[str, Any] = {"input": {}}

    event = FakeEvent()

    ctx.update_event(event, logger)

    assert event.tool_use["input"]["lat"] == 41.0
    assert event.tool_use["input"]["lang"] == -87.0
    assert event.tool_use["input"]["plan"] == "Choice Plus"
    assert any("Tool input is updated" in m for m in logger.messages)


def test_update_event_no_matching_keys():
    """If tool schema doesn't expose lat/lang/plan, nothing should be injected."""
    logger = DummyLogger()
    ctx = AgentRequestContext(lat=41.0, lang=-87.0, plan="Choice")

    class FakeSelectedTool:
        def __init__(self):
            self.spec = {
                "inputSchema": {
                    "json": {
                        "properties": {
                            "foo": {"type": "string"},
                        }
                    }
                }
            }

    class FakeEvent:
        def __init__(self):
            self.selected_tool = FakeSelectedTool()
            self.tool_use = {"input": {}}

    event = FakeEvent()

    ctx.update_event(event, logger)

    assert event.tool_use["input"] == {}
    assert any("No parameter updated for tool input" in m for m in logger.messages)

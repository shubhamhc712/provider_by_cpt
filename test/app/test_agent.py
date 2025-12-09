# tests/test_app_agent.py

import pytest

import app.agent as agent_module


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg: str, *args, **kwargs):
        self.messages.append(msg)

    def exception(self, msg: str, *args, **kwargs):
        self.messages.append(msg)


@pytest.mark.asyncio
async def test_invoke_streams_data(monkeypatch):
    """invoke should stream out 'data' fields from the underlying agent."""

    logger = DummyLogger()
    payload = {"prompt": "Find providers"}

    class FakeAgentCoreContext:
        @staticmethod
        def get_context():
            return object()

    class FakeCtx:
        def model_dump(self):
            return {}

    class FakeAgentRequestContext:
        @staticmethod
        def from_agent_core_context(_ctx):
            return FakeCtx()

    monkeypatch.setattr(agent_module, "AgentCoreContext", FakeAgentCoreContext, raising=False)
    monkeypatch.setattr(agent_module, "AgentRequestContext", FakeAgentRequestContext, raising=False)

    class FakeMcpFactory:
        async def get_mcp_client(self):
            return object()

    mcp_factory = FakeMcpFactory()

    class FakeAgent:
        async def stream_async(self, user_input: str):
            yield {"data": "part-1"}
            yield {"data": "part-2"}
            yield {"other": "ignore"}

    class FakeAgentFactory:
        async def create_agent(self, tool_factory, state):
            assert isinstance(state, dict)
            # tool_factory() would return MCP tools; we don't validate here
            return FakeAgent()

    agent_factory = FakeAgentFactory()

    chunks = []
    async for item in agent_module.invoke(
        mcp_client_factory=mcp_factory,
        agent_factory=agent_factory,
        logger=logger,
        payload=payload,
    ):
        chunks.append(item)

    assert chunks == ["part-1", "part-2"]


@pytest.mark.asyncio
async def test_invoke_handles_exception(monkeypatch):
    """If the underlying agent raises, invoke should catch and yield an error message."""

    logger = DummyLogger()
    payload = {"prompt": "Cause error"}

    class FakeAgentCoreContext:
        @staticmethod
        def get_context():
            return object()

    class FakeCtx:
        def model_dump(self):
            return {}

    class FakeAgentRequestContext:
        @staticmethod
        def from_agent_core_context(_ctx):
            return FakeCtx()

    monkeypatch.setattr(agent_module, "AgentCoreContext", FakeAgentCoreContext, raising=False)
    monkeypatch.setattr(agent_module, "AgentRequestContext", FakeAgentRequestContext, raising=False)

    class FakeMcpFactory:
        async def get_mcp_client(self):
            return object()

    mcp_factory = FakeMcpFactory()

    class FakeAgent:
        async def stream_async(self, user_input: str):
            raise RuntimeError("boom")

    class FakeAgentFactory:
        async def create_agent(self, tool_factory, state):
            return FakeAgent()

    agent_factory = FakeAgentFactory()

    chunks = []
    async for item in agent_module.invoke(
        mcp_client_factory=mcp_factory,
        agent_factory=agent_factory,
        logger=logger,
        payload=payload,
    ):
        chunks.append(item)

    assert len(chunks) == 1
    assert "Error occurred while processing your request" in chunks[0]
    assert any("Error during agent invocation" in m for m in logger.messages)

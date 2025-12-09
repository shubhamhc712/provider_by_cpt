# tests/test_mcpserver.py

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

import mcpserver


@pytest.mark.asyncio
async def test_gap_exception_service_builds_url_and_params(monkeypatch):
    """MCP gap_exception_service should call /v1/search with correct params and return response.text."""

    mcpserver.settings = SimpleNamespace(gap_exception_service_url="http://test-service")

    class FakeResponse:
        def __init__(self, text):
            self.text = text
            self.raised = False

        def raise_for_status(self):
            self.raised = True

    class FakeHttpxClient:
        def __init__(self):
            self.calls: List[Dict[str, Any]] = []

        async def get(self, url, params):
            self.calls.append({"url": url, "params": params})
            return FakeResponse("OK")

    fake_client = FakeHttpxClient()
    monkeypatch.setattr(mcpserver, "httpx_client", fake_client, raising=False)

    result = await mcpserver.gap_exception_service(
        cpt_codes=["D2750", "D1111"],
        lat=41.0,
        lng=-87.0,
        radius_in_meters=5000.0,
        plan="Choice",
        skip=0,
        limit=5,
    )

    assert result == "OK"
    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["url"] == "http://test-service/v1/search"
    assert call["params"]["cpt_code"] == ["D2750", "D1111"]
    assert call["params"]["lat"] == 41.0
    assert call["params"]["lng"] == -87.0
    assert call["params"]["radius_in_meters"] == 5000.0
    assert call["params"]["plan"] == "Choice"
    assert call["params"]["skip"] == 0
    assert call["params"]["limit"] == 5

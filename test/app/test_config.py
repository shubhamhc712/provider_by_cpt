# tests/test_app_config.py

import os
from types import SimpleNamespace

from app.config import GapExceptionConfig, GapExceptionEnvSettings, get_gap_exception_config


def _make_min_config() -> GapExceptionConfig:
    return GapExceptionConfig(
        memory_id="mem-123",
        lim_project_id="proj-1",
        llm_client_id="client",
        llm_client_secret="secret",
        llm_token_url="https://example.com/token",
        llm_scope="scope",
        llm_target_env="dev",
        llm_model_id="model-id",
        mcp_url="https://mcp.example.com",
    )


def test_update_env_variables_sets_azure_env():
    cfg = _make_min_config()

    cfg.update_env_variables()

    assert os.environ["AZURE_API_BASE"] == cfg.azure_api_base
    assert os.environ["AZURE_API_VERSION"] == cfg.azure_api_version


def test_create_llm_key_refresher(monkeypatch):
    from app import config as cfg_module

    cfg = _make_min_config()
    captured = {}

    class FakeRefresher:
        def __init__(self, client_id, client_secret, token_url, scope, target_env, httpx_async_client, logger):
            captured["client_id"] = client_id
            captured["client_secret"] = client_secret
            captured["token_url"] = token_url
            captured["scope"] = scope
            captured["target_env"] = target_env

    monkeypatch.setattr(cfg_module, "Oauth2KeyRefresher", FakeRefresher, raising=False)

    refresher = cfg.create_lim_key_refresher(async_client=object(), logger=object())
    assert isinstance(refresher, FakeRefresher)
    assert captured["client_id"] == cfg.llm_client_id
    assert captured["token_url"] == cfg.llm_token_url


def test_create_mcp_key_refresher_none_when_missing():
    cfg = _make_min_config()
    cfg.mcp_client_id = None
    cfg.mcp_client_secret = None
    cfg.mcp_token_url = None
    cfg.mcp_scope = None

    refresher = cfg.create_mcp_key_refresher(async_client=object(), logger=object())
    assert refresher is None


def test_create_mcp_key_refresher_non_none(monkeypatch):
    from app import config as cfg_module

    cfg = _make_min_config()
    cfg.mcp_client_id = "mcp-client"
    cfg.mcp_client_secret = "mcp-secret"
    cfg.mcp_token_url = "https://mcp.example.com/token"
    cfg.mcp_scope = "mcp-scope"

    captured = {}

    class FakeRefresher:
        def __init__(self, client_id, client_secret, token_url, scope, httpx_async_client, logger):
            captured["client_id"] = client_id
            captured["token_url"] = token_url

    monkeypatch.setattr(cfg_module, "Oauth2KeyRefresher", FakeRefresher, raising=False)

    refresher = cfg.create_mcp_key_refresher(async_client=object(), logger=object())
    assert isinstance(refresher, FakeRefresher)
    assert captured["client_id"] == cfg.mcp_client_id


def test_create_llm_model(monkeypatch):
    from app import config as cfg_module

    cfg = _make_min_config()
    cfg.lim_project_id = "proj-123"  # or cfg.llm_project_id if that's the field name in your code

    captured = {}

    class FakeModel:
        def __init__(self, model_id, params):
            captured["model_id"] = model_id
            captured["params"] = params

    # Your code referenced LiteLLMModel
    monkeypatch.setattr(cfg_module, "LiteLLMModel", FakeModel, raising=False)

    model = cfg.create_llm_model()
    assert isinstance(model, FakeModel)
    assert captured["model_id"] == cfg.llm_model_id
    assert captured["params"]["extra_headers"]["projectId"] == cfg.lim_project_id


def test_create_mcp_client_factory(monkeypatch):
    from app import config as cfg_module

    cfg = _make_min_config()
    captured = {}

    class FakeFactory:
        def __init__(self, mcp_url, key_refresher, logger):
            captured["mcp_url"] = mcp_url
            captured["key_refresher"] = key_refresher

    monkeypatch.setattr(cfg_module, "StreamableHttpMcpClientFactory", FakeFactory, raising=False)

    factory = cfg.create_mcp_client_factory(key_refresher="REFRESHER", logger=object())
    assert isinstance(factory, FakeFactory)
    assert captured["mcp_url"] == cfg.mcp_url
    assert captured["key_refresher"] == "REFRESHER"


def test_create_memory_hooks(monkeypatch):
    from app import config as cfg_module

    cfg = _make_min_config()
    cfg.aws_region = "us-east-1"
    cfg.memory_id = "mem-xyz"

    captured = {}

    class FakeMemoryClient:
        def __init__(self, region_name):
            captured["region_name"] = region_name

    class FakeHooks:
        def __init__(self, memory_id, client, logger, agent_init_number_of_events, customer_context_top_k):
            captured["memory_id"] = memory_id
            captured["agent_init_number_of_events"] = agent_init_number_of_events
            captured["customer_context_top_k"] = customer_context_top_k

    monkeypatch.setattr(cfg_module, "MemoryClient", FakeMemoryClient, raising=False)
    monkeypatch.setattr(cfg_module, "AskAiSearchMemoryHooks", FakeHooks, raising=False)

    hooks = cfg.create_memory_hooks(logger=object())
    assert isinstance(hooks, FakeHooks)
    assert captured["memory_id"] == cfg.memory_id
    assert captured["agent_init_number_of_events"] == cfg.memory_agent_init_number_of_events
    assert captured["customer_context_top_k"] == cfg.memory_customer_context_top_k


def test_get_gap_exception_config_builds_ssm_path(monkeypatch):
    from app import config as cfg_module

    class FakeSSM:
        pass

    captured = {}

    def fake_get_json_ssm_parameter(name, ssm):
        captured["name"] = name
        captured["ssm"] = ssm
        return {
            "memory_id": "mem-1",
            "lim_project_id": "proj-1",
            "llm_client_id": "cid",
            "llm_client_secret": "sec",
            "llm_token_url": "https://token",
            "llm_scope": "scope",
            "llm_target_env": "dev",
            "llm_model_id": "model",
            "mcp_url": "https://mcp",
        }

    monkeypatch.setattr(cfg_module, "get_json_ssm_parameter", fake_get_json_ssm_parameter, raising=False)

    env_settings = GapExceptionEnvSettings(env="dev")
    cfg = get_gap_exception_config(env_settings=env_settings, ssm=FakeSSM())

    assert isinstance(cfg, GapExceptionConfig)
    assert captured["name"] == "/askai/search/gap-exception/dev/config"

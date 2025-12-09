import os
from logging import Logger
from typing import Optional
from unittest import result

from bedrock_agentcore.memory import MemoryClient
from httpx import AsyncClient
from optum_us_ml_gen_ai_common_basic.ssm import get_json_ssm_parameter
from optum_us_ml_gen_ai_common_basic.security.Keyrefresher import Oauth2KeyRefresher , KeyReferenceConfig
from optum_us_ml_gen_ai_common_strands.mcp import StremableHttpMcpClientFactory
from optum_us_ml_gen_ai_common_strands.memory.agentcorememory import AskAiSearchMemoryHooks
from pydantic import BaseModel
from pydentic_settings import BaseSettings , SettingsConfigDict
from strands.models import Model
from strands.model.litellm import LiteLLModel

class GapExceptionEnvSettings(BaseSettings):
    env:str = "dev"

    model_config = SettingsConfigDict(env_prefix = 'askai_search_gap_exception_')

class GapExceptionConfig(BaseModel):
    azure_api_base: str = "https://api.uhg.com/api/cloud/api-management/ai-gateway/1.0"
    azure_api_version: str = "2025-01-01-preview"
    memory_id: str
    aws_region: str = "us-east-1"
    memory_agent_init_number_of_events: int = 20
    memory_customer_context_top_k: int = 3
    lim_project_id: str
    llm_client_id: str
    llm_client_secret: str
    llm_token_url: str
    llm_scope: str
    llm_target_env: str
    llm_model_id: str
    mcp_url: str
    mcp_client_id: Optional [str] = None
    mcp_client_secret: Optional[str] = None
    mcp_token_url: Optional[str] = None
    mcp_scope: Optional [str] = None

    def update_env_variables(self):
         os.environ["AZURE_API_BASE"] = self.azure_api_base
         os.environ["AZURE_API_VERSION"] = self.azure_api_version

    def create_lim_key_refresher(self, async_client: AsyncClient, logger: Logger) -> KeyRefresher:
         return Oauth2KeyRefresher(
            client_id=self.llm_client_id,
            client_secret=self.llm_client_secret,
            token_url=self.llm_token_url,
            scope=self.llm_scope,
            target_env=self.llm_target_env,
            httpx_async_client=async_client,
            logger=logger
        )

    def create_mcp_key_refresher(self, async_client: AsyncClient, logger: Logger) -> Optional [KeyRefresher]:
        if self.mcp_client_id and self.mcp_client_secret and self.mcp_token_url and self.mcp_scope:
            return Oauth2KeyRefresher(
                client_id=self.mcp_client_id,
                client_secret=self.mcp_client_secret,
                token_url=self.mcp_token_url,
                scope=self.mcp_scope,
                httpx_async_client=async_client,
                logger=logger
            )
        return None

    def create_llm_model(self) -> Model:
        return LiteLLMModel(
            model_id=self.llm_model_id,
            params={
                "extra_headers": {
                    "projectId": self.llm_project_id
                }
            }
        )

    def create_mcp_client_factory(self, key_refresher: KeyRefresher, logger: Logger) -> StreamableHttpMcpClientFactory:
        return StreamableHttpMcpClientFactory(
            mcp_url=self.mcp_url,
            key_refresher=key_refresher,
            logger=logger
        )
    def create_memory_hooks(
            self,
            logger: Logger ,
            memory_client: Optional [MemoryClient] = None
    )-> AskAiSearchMemoryHooks:
        return AskAiSearchMemoryHooks(
            memory_id=self.memory_id,
            client=memory_client if memory_client is not None else self.create_memory_client(),
            logger=logger,
            agent_init_number_of_events=self.memory_agent_init_number_of_events,
            customer_context_top_k=self.memory_customer_context_top_k
        )

    def create_memory_client(self) -> MemoryClient:
        return MemoryClient(region_name=self.aws_region)

    def get_gap_exception_config(env_settings: GapExceptionEnvSettings, ssm) -> GapExceptionConfig:
        ssm_parameter_name = f"/askai/search/gap-exception/{env_settings.env}/config"
        config_dict = get_json_ssm_parameter(
            name=ssm_parameter_name,
            ssm=ssm
        )
        result = GapExceptionConfig(**config_dict)
        return result
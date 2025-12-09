import logging
from logging import Logger
from typing import Dict , Any

import boto3
from bedrock_agentcore.runtime import (
    BedrockAgentCoreApp,
)

from httpx import AsyncClient
from optum_us_ml_gen_ai_common_strands.agent.agentfactory import KeyReferenceAgentFactory , AgentFactory
from optum_us_ml_gen_ai_common_strands.agent.agentlogging import init_logging
from optum_us_ml_gen_ai_common_strands.agent.context import AgentContext
from optum_us_ml_gen_ai_common_strands.mcp import StremableHttpMcpClientFactory
from optum_us_ml_gen_ai_common_strands.mcp import get_mcp_tools

from app.config import get_gap_exception_config , GapExceptionEnvSettings
from app.context import AgentRequestContext
from app.hooks import RequestContextInjectingHook

SYSTEM_PROMPT = """
You are a healpful assistant . You are an expert in finding providers.
Please use the provided tools to find providers based on user queries.
When calling the tool, it is OK if lat, lang, and plan are not porived. It will be injected from state.

When returning providers:
-Create a url link on their name to the web url returned by the tool.
-At minimum, include their specialty, name, address, phone number, and distance in miles from the provided location.
"""

async def invoke(
        mcp_client_factory: StremableHttpMcpClientFactory,
        agent_factory:AgentFactory,
        logger: Logger,
        payload: Dict[str, Any],
        
):
    agent_core_context = AgentCoreContext.get_context()
    request_context = AgentRequestContext.from_agent_core_context(agent_core_context)
    user_input = payload["prompt"]
    mcp_client = await mcp_client_factory.get_mcp_client()
    my_agent = await agent_factory.create_agent(
        tool_factory = lambda: get_mcp_tools(mcp_client),
        state=request_context.model_dump()
    )

    try:
        async for event in my_agent.stream_async(user_input):
            if "data" in event:
                yield event["data"]
    except Exception as e:
        logger.exception(f"Error during agent invocation: {str(e)}" , exc_info=True)
        yield f"Error occurred while processing your request. Please try again later."

def create_app(system_prompt: str) -> BedrockAgentCoreApp:
    logger = logging.getLogger("app.agent")
    init_logging(logger , log_level=logging.INFO)
    logger.info("Starting application...")
    ssm = boto3.client("ssm")
    env_settings = GapExceptionEnvSettings()
    config = get_gap_exception_config(env_settings = env_settings , ssm=ssm)
    config.update_env_variable()
    async_client =AsyncClient()
    llm_key_refresher = config.create_llm_key_refresher(async_client = async_client ,logger=logger)
    mcp_key_refresher = config.create_mcp_key_refresher(async_client=async_client , logger=logger)
    model = config.create_llm_model()
    memory_hooks = config.create_memory_hooks(logger)

    agent_factory = KeyReferenceAgentFactory(
        key_refresher = llm_key_refresher,
        model = model,
        system_prompt = system_prompt,
        hooks=[
            memory_hooks,
            RequestContextInjectingHook(logger=logger)
        ]
    )
    mcp_client_factory = config.create_mcp_client_factory(key_refresher = mcp_key_refresher , logger=logger)

    app = BedrockerAgentCoreApp()
    app.enterypoint(lambda payload: invoke(
        agent_factory=agent_factory,
        mcp_client_factory=mcp_client_factory,
        logger=logger,
        payload=payload
    ))
    logger.info("Application initialized..")
    return app

if __name__ == "__main__":
    create_app(system_prompt=SYSTEM_PROMPT).run()
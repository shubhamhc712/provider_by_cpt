from contextlib import asynccontextmanager
from logging import Logger
import platform
from typing import Annotated, Optional

import boto3
import fastapi
import yaml
from fastapi import FastAPI, Request, Depends, Query
from fastapi.responses import Response
from httpx import AsyncClient
from optum_us_ml_gen_ai_common_basic.aws.headers import HDR_TRACE_ID
from optum_us_ml_gen_ai_common_basic.aws.trace import make_trace_id
from optum_us_ml_gen_ai_common_strands.agent.chat import AWS4AuthChatService, ChatService
from optum_us_plt_fastapi_platform.apphealth import mark_app_as_healthy
from optum_us_plt_fastapi_platform.pltfastapi import UsPlatformFastApi 
from optum_us_ml_gen_ai_common_basic.security.authparser import BasicJwtVerifier, BasicJwtTokenParser

from pymongo import AsyncMongoClient
from app.constants import HDR_LAT, HDR_LNG
from app.dto import FindDetailInput, SearchInput, SearchResult, ChatRequest, FindByKeyInput, Provider
from app.service import GapExceptionService, GapExceptionServiceImpl
from app.settings import GapExceptionServiceSettings, ServiceMode

_svc: Optional [GapExceptionService] = None

_chat: Optional [ChatService] = None

_auth_checker: Optional['AuthChecker'] = None

def get_gap_exception_service() -> GapExceptionService:
    return _svc

def get_chat_service() -> ChatService:
    return _chat

def get_auth_checker() -> AuthChecker:
    return _auth_checker

settings = GapExceptionServiceSettings()

@asynccontextmanager
async def setup(_: FastAPI):
    global _svc
    global _chat
    global _auth_checker
    logger = UsPlatformFastApi.create_app_logger()
    try:
        secrets_manager = boto3.client("secretsmanager")
        mongo = AsyncMongoClient(
            settings.get_mongo_url(secrets_manager)
        )

        _svc = GapExceptionServiceImpl(
            mongo=mongo,
            db_name=settings.db_name,
            provider_collection_name=settings.provider_collection_name,
            provider_index_name=settings.provider_index_name,
            plan_collection_name=settings.plan_collection_name,
            plan_index_name=settings.plan_index_name,
            distance_weight=settings.distance_weight,
            cpt_score_weight=settings.cpt_score_weight,
            provider_base_url=settings.provider_base_url,
            logger=logger
        )
        if settings.service_mode == ServiceMode.CHAT:
            async_client = AsyncClient()
            _chat = AWS4AuthChatService(
                httpx_client=async_client,
                logger=logger,
                agent_arn=settings.chat_agent_arn,
            )

            if settings.msid_auth_enabled:
                jwt_verifier = None #You can initialize your JWT verifier here if needed
                if settings.is_msid_token_verifier_needed():
                    client_secret = settings.get_msid_client_secret(secrets_manager)
                    if not client_secret:
                        raise ValueError(
                            "MSID client secret is not set in secrets manager.")
                    jwt_verifier = BasicJwtVerifier(
                        async_client=async_client,
                        client_id=settings.msid_token_client_id,
                        client_secret=client_secret,
                        token_url = settings.msid_token_url,
                        logger=logger
                    )
                
                else:
                    logger.info("MSID auth is disabled or configuaration is incomplete.")

                token_parser = BasicJwtTokenParser(
                    verifier= jwt_verifier,
                    error_when_exp=not settings.msid_auth_allow_expired,
                )
                _auth_checker = BasicAuthChecker(
                    token_parser=token_parser
                )
            else:
                logger.info("MSID auth is disabled for the service.")
        
        mark_app_as_healthy()
        logger.info("Application initialized")
        yield
        logger.info("Application terminated")
    except Exception as e:
        logger.exception("Unable to initialize application:{e}", exc_info=True)
        raise e

plt_fastapi_app = UsPlatformFastApi(
    fast_api_lifespan=setup
)

def get_logger():
    return plt_fastapi.logger

app = plt_fastapi.application

@app.get(
    "/v1/search_providers",
    summary="Search provider based on the provided parameters.",
    description="Search provider based on the given parameters.",
)
async def search_providers(
        param:Annotated[SearchInput, Query()],
        request: Request,
        service: GapExceptionService = Depends(get_gap_exception_service)
) -> SearchResult:
    return await service.search_providers(param, request)

async def get_subject(
        request:Request,
        logger: Logger,
        auth_checker: Optional[AuthChecker]
):
    if auth_checker:
        claims = await auth_checker.check_auth(request)
        return claims["sub"]
    else:
        logger.error("Auth checker is not configured for subject extraction. This should be only in local")
        return None

if settings.service_mode == ServiceMode.CHAT:
    @app.post(
        "/v1/chat",
        summary="Chat with the Gap Exception service.",
        description="Engage in a chat session with the Gap Exception service.",
    )
    async def chat_endpoint(
            param: ChatRequest,
            request: Request,
            chat_svc: ChatService = Depends(get_chat_service),
            logger: Logger = Depends(get_logger),
            auth_checker: AuthChecker = Depends(get_auth_checker)
    ):
        trace_id = f"{make_trace_id()}"
        actor_id = await get_subject(request, logger, auth_checker)
        actor_id = actor_id if actor_id is not None else param.session_id

        logger.info(
            f"Chat request received with session_ids: {param.session_id}, trace_id: {trace_id}, actor_id: {actor_id}"
        )

        headers = {
            HDR_LAT: str(param.lat),
            HDR_LNG: str(param.lng),
            HDR_TRACE_ID: trace_id
        }
        if param.network_id:
            headers[HDR_NETWORK_IDS] = ",".join(param.network_id)
        return chat_svc.starlette_chat(
            session_id=param.session_id,
            actor_id=actor_id,
            payload={"prompt": param.prompt},
            request=request,
            header_args=headers
        )
    
    @app.get(
        "/v1/provider",
        summary="Find provider details",
        description="Find provider details by unique key.",
        response_model=FindKeyResult
    )
    async def find_provider_details(
        param: Annotated[FindDetailInput, Query()],
        request : Request,
        service: GapExceptionService = Depends(get_gap_exception_service),
        logger: Logger = Depends(get_logger),
        auth_checker: AuthChecker = Depends(get_auth_checker)
    ):
        #Dont really need to get the subject here, but just to make sure the auth is checked
        await get_subject(request, logger, auth_checker)
        result = await service.find_provider_detail(
            param,
            request
        )
        if result is None:
            raise ValueError(f"No Provider found for  {param.model_dump_json()}")
        return FindByKeyInput(
            data=result,
            input_param = param
        )
    
    @app.get(
        "/v1/search_plans",
        summary="Search for insurance plan details.",
        description="Search for insurance plan details based on provided parameters.",
        response_model=SearchPlanResult
    )
    async def search_plans(
        param: Annotated[SearchPlanInput, Query()],
        request : Request,
        service: GapExceptionService = Depends(get_gap_exception_service),
        logger: Logger = Depends(get_logger),
        auth_checker: AuthChecker = Depends(get_auth_checker)
    ):
        #Dont really need to get the subject here, but just to make sure the auth is checked
        await get_subject(request, logger, auth_checker)
        result = await service.search_plans(
            param,
            request
        )

#Below can be uncommented for local testing if you want to serve static html files
app.mount("/static", StaticFiles(directory="static"), name="static")
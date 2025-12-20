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

from pymongo import AsyncMongoClient
from app.constants import HDR_LAT, HDR_LNG
from app.dto import SearchInput, SearchResult, ChatRequest, FindByKeyInput, Provider
from app.service import GapExceptionService, GapExceptionServiceImpl
from app.settings import GapExceptionServiceSettings, ServiceMode

_svc: Optional [GapExceptionService] = None

_chat: Optional [ChatService] = None

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
            db_name=settings.mongo_db_name,
            collection_name=settings.mongo_collection_name,
            index_name=settings.mongo_search_index_name,
            search_score_weight=settings.search_score_weight,
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

                token_parser = B
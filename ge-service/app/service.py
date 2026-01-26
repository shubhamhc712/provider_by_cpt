import json
from pydoc import doc
import time
from abc import ABC, abstractmethod
from logging import Logger
from typing import List, Union, Dict, Any, Optional
from unittest import result

from altair import param
from fastapi import Request
from optum_us_ml_gen_ai_common_basic.lang.listutil import add_items_when_not_none
from pymongo import AsyncMongoClient

from dto import SearchPlanInput, Provider , SearchResult, ProviderSummary, GeoCode, \
LocationInput, SearchPlanResult, Plan , SearchPlanInput ,FindDetailInput
from app.dto import SearchInput, Provider, SearchResult, GeoCode

FLATTEN_DIR_NETWORK = {
    #Flatten the array of arrays"
    "$reduce": {
        "input": "$directory_network",
        "initialValue": [],
        "in": {
            "$concatArrays": ["$$value", "$$this"]
        }
    }
}

PROJ_ASSOCIATED_CPTS = "associated_cpts"
REF_ASSOC_CPT = f"${PROJ_ASSOCIATED_CPTS}"


class GapExceptionService (ABC):
    @abstractmethod
    async def search(
            self,
            param: SearchInput,
            request: Request
    ):
        """
        Perform search based on the provided parameters.
        
        :param param: The search parameter
        :param request: The incoming request
        : return:
        """

    @abstractmethod
    async def find_provider_detail(
            self,
            key: str,
            request: Request,
    ) -> Provider:
        """
        Find a provider by its generated key.
    
        :param key: The input parameter
        :param request: The FastAPI request. Only used for json_logging.
        :return: The provider if found, else None
        """

    @abstractmethod
    async def search_plan(self, param: SearchPlanInput, request: Any) -> SearchPlanResult:
        """
        Find plan information based on the parameters..
        
        :param param: The search parameter
        :param request: The FastAPI request. Only used for json_logging.
        :return: List of plans
        """

class GapExceptionServiceImpl(GapExceptionService):
    def __init__(
            self,
            mongo: AsyncMongoClient,
            db_name: str,
            provider_collection_name: str,
            provider_index_name: str,
            plan_collection_name: str,
            plan_index_name: str,
            distance_weight: float,
            cpt_score_weight: float,
            provider_base_url: str,
            logger: Logger,
            distance_pivot: int = 1000,
            search_early_limit = 500
    ):
        self.mongo = mongo
        self.db_name = db_name
        self.provider_collection_name = provider_collection_name
        self.provider_index_name = provider_index_name
        self.plan_collection_name = plan_collection_name
        self.plan_index_name = plan_index_name
        self.distance_weight = distance_weight
        self.cpt_score_weight = cpt_score_weight
        self.provider_base_url = provider_base_url
        self.logger = logger
        self.distance_pivot = distance_pivot
        self.search_early_limit = search_early_limit

    async def find_by_key(
            self,
            param: FindDetailInput,
            request: Any,
    ) -> Optional [Provider]:
       start_time = time.perf_counter()

       mql = self.create_find_mql(param)
       self.logger.info(f"For input: {param.model_dump_json()}, generated mql: {json.dumps(mql)}")
       query_result = await self.mongo[self.db_name][self.provider_collection_name].aggregate(mql)
       origin = param.get_search_origin()

       result = None
       async for doc in query_result:
           result = Provider.from_doc(doc, origin)


       elapsed_time_ms = int((time.perf_counter() - start_time) * 1000)
       self.logger.info(
           f"Provider found: {result is not None}, elapsed time {elapsed_time_ms} ms for search with "
           f"key: {param.key}, db name: {self.db_name}, collection name: {self.provider_collection_name},"
           f"index name: {self.provider_index_name}, param: {param.model_dump_json()}"
        )
        return result
    
    async def search(
            self,
            param: SearchInput, 
            request: Request
    ) -> SearchResult:
        mql = self.create_mql(param)
        if len(mql) == 0:
            self.logger.info("Search parameters are empty, returning no results.")
            return SearchResult(data=[])
        try:
            start_time = time.perf_counter()
            async_cursor = await self.mongo[self.db_name][self.collection_name].aggregate(mql)
            providers = [Provider.from_doc(
                doc,
                self.provider_base_url,
                param.get_search_origin() 
            ) async for doc in async_cursor]

            end_time = time.perf_counter()
            elapsed_time_ms = int((end_time - start_time) * 1000)
            self.logger.info(
                f"Found {len(providers)} results with elapsed time {elapsed_time_ms} ms for search with "
                f"param: {param.model_dump()}, db name: {self.db_name}, collection name: {self.collection_name},"
                f"index name: {self.index_name}"
            )
            self.logger.info(f"MQL executed: {json.dumps(mql)}")
            return SearchResult(data=providers)
        except Exception as e:
            self.logger.error(f"Error occurred: {str(e)} mql: {json.dumps(mql)}", exc_info=True) 
            raise e

def create_mql(
        self,
        param: SearchInput
):
    must = add_items_when_not_none( 
        input_list=[], 
        flatten_item=True, 
        items=[ 
            self.create_cpt_code_filter(param), 
            self.create_location_filter(param), 
            self.create_plan_filter(param)
        ]
    )
    
    if len(must) == 0:
        return []
    
    return [
        {
            " $search": {
                "index": self.index_name, }
                "compound": {
                    "must": must
                }
            }
        },
        {
            "$addFields": {
                "search_score": {"$meta": "searchScore"}
            }
        },
        {
            "$addFields": {
                "cpt_code_sum": self.create_cpt_code_sum_projection(param.cpt_codes)
            }
        },
        {
            "$addFields": {
                "relevance_score": {
                    "$add": [
                        {
                            "$multiply": ["$search_score", self.search_score_weight]
                        },
                        {
                            "$multiply": ["$cpt_code_sum", self.cpt_score_weight]
                        }
                    ]
                }
            }
        },
        {
             "$sort": {
                "relevance_score": -1 # Sort by relevance score in descending order
            }
        },
        {
            "$skip": param.skip # Skip the specified number of records
        },
        {
            "$limit": param.limit # Limit the number of results
        }
    ]

@staticmethod
def create_cpt_code_filter(
    param: SearchInput
):
    if not param.cpt_codes:
        return None
    return ({
        "in": {
            "path": "cpt_counts.code", 
            "value": param.cpt_codes 
        }
    })

@staticmethod
def create_location_filter(
    param: SearchInput
):
    if not param.lat or not param.lng:
        return None
    return [
        {
            "geoWithin": {
                "path": "address.geoCode",
                "circle": {
                    "center": {
                        "type": "Point",
                         "coordinates": [
                            param.lng,
                            param.lat
                        ]
                    }
                    "radius": param.radius_in_meters
                }
            }
        },
        {
            "near": {
                "path": "address.geoCode",
                "origin": {
                    "type": "Point",
                    "coordinates": [
                        param.lng,
                        param.lat
                    ]
                }
                "pivot"; 1000,
            }
        }
    ]

@staticmethod
def create_plan_filter(
        param: SearchInput
):
    if not param.plan:
            return None
    return ({
        "in": {
            "path": "networkID", # This may not be correct, but let's put it like this for now
            "value": [param.plan]
        }
    })

@staticmethod
def create_cpt_code_sum_projection(cpt_codes: List[str]) -> Union [int, Dict [str, Any]]:
    if cpt_codes is None or len(cpt_codes) == 0:
        return 0
    return {
        "$reduce": {
            "input": "$cpt_counts",
            "initialValue": 0,
            "in": {
                "$add": [
                    "$$value",
                    {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {"$in": ["$$this.code", cpt_codes]},
                                    "then": "$$this.count"
                                }
                            ],
                            "default": 0
                        }
                    }
                ]
            }
        }
    }
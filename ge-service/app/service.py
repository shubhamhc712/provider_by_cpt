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

from app.dto import SearchInput, Provider, SearchResult, GeoCode


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
    async def find_by_key(
        self,
        key: str,
        request: Request,
        lat: Optional [float] = None,
        lng: Optional [float] = None
    ) -> Optional [Provider]:
        """
        Find a provider by its generated key.
    
        :param key: The generated key of the provider
        :param lat: Optional latitude for location context
        :param lng: Optional longitude for location context
        :param request: The incoming request
        :return: The provider if found, else None
    """

class GapExceptionServiceImpl(GapExceptionService):
    def __init__(
            self,
            mongo: AsyncMongoClient,
            db_name: str,
            collection_name: str,
            index_name: str,
            search_score_weight: float,
            cpt_score_weight: float,
            provider_base_url: str,
            logger: Logger
    ):
        self.mongo = mongo
        self.db_name = db_name
        self.collection_name = collection_name
        self.index_name = index_name
        self.search_score_weight = search_score_weight
        self.cpt_score_weight = cpt_score_weight
        self.provider_base_url = provider_base_url
        self.logger = logger

    async def find_by_key(
            self,
            key: str,
            request: Request,
            lat: Optional [float]  = None,
            lng: Optional [float] = None
    ) -> Optional [Provider]:
        start_time = time.perf_counter()
        query_result = await self.mongo [self.db_name] [self.collection_name].find_one({"_id": key})

        origin = None
        if lat is not None and lng is not None:
            origin = GeoCode(
                lat=lat,
                lng=lng
            )
        result = None
        if query_result:
            return Provider.from_doc(
                query_result, 
                self.provider_base_url, 
                origin
            )

        elapsed_time_ms = int((time.perf_counter() - start_time) * 1000)
        self.logger.info(
            f"Provider found: (result is not None), elapsed time {elapsed_time_ms} ms for search with "
            f"key: {key}, lat: {lat}, lng: {lng}, db name: {self.db_name}, collection name: {self.collection_name},"
            f"index name: {self.index_name}"
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
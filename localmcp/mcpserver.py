import logging
from typing import List, Optional

from httpx import AsyncClient
from mcp.server import FastMCP
from pydantic_settings import BaseSettings

class MCPSetting(BaseSettings):
    gap_exception_service_url: str = "http://localhost:8001"

#Create MCP server
mcp = FastMCP("GAP Exception MCP Server")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting MCP Server")

httpx_client = AsyncClient()
setting = MCPSetting()

@mcp.tool(description="The service to pull various provider data for gap exception project")
async def gap_exception_service(
    cpt_codes: Optional[List[str]],
    lat: Optional[float],
    lng: Optional[float],
    radius_in_meters: float ,
    plan: Optional[str],
    skip: Optional[int],
    limit: Optional[int]
):
    """
    Fetch provider data from gap exception service based on the provided parameters.

    :param cpt_code: The CPT codes to search for.
    :param lap: The latitude for location-based search.
    :param lng: The longitude for location-based search.
    :param radius_in_meters: The search radius in meters.It will be ignored if lat/lng is not provided.
    :param plan: The member insurance plan to consider during the search.
    :param skip: Number of records to skip for pagination.
    :param limit: Maximum number of records to return
    :return: The provider information
    """
    url = f"{settings.gap_exception_service_url}/v1/search"

    params = {
        "cpt_code": cpt_codes,
        "lat": lat,
        "lng": lng,
        "radius_in_meters": radius_in_meters,
        "plan": plan,
        "skip": skip,
        "limit": limit
    }

    #delete on params that are None
    params = {k: v for k, v in params.items() if v is not None}
    logger.info(f"Calling Gap Exception Service at {url} with params: {params}")
    response = await httpx_client.get(
        url=url,
        params=params,
    )
    response.raise_for_status()
    return response.text

logging.info("MCP Server is initialized...")

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
from typing import Optional, List, Any, Mapping
from unittest import result

from geopy.distance import great_circle 
from pydantic import BaseModel, Field

class SearchInput (BaseModel):
    cpt_codes: Optional [List [str]] = Field(
        description="The CPT code to search for.",
        default=None
    )
    lat: Optional [float] = Field(
        description="The latitude for location-based search.",
        default=None
    )
    lng: Optional [float] = Field(
        description="The longitude for location-based search.",
        default=None
    )
    radius_in_meters: float = Field(
        description="The search radius in meters. It will be ignored if lat/lng is not provided.",
        default=48280.3 # 30 miles in meters
    )
    plan: Optional [str] = Field(
        description="The member insurance plan to consider during the search.",
        default=None
    )
    skip: Optional [int] = Field(
        description="Number of records to skip, for pagination",
        default=0
    )
    limit: Optional [int] = Field(
        description="Maximum number of results to return",
        default=5
    )

    def get_search_origin(self):
      result = None
      if self.lat is not None and self.lng is not None:
         result = GeoCode(lat=self.lat, lng=self.lng)
      return result

class Degree(BaseModel):
    code: str = Field(
        description="The degree code, e.g., DMD"
    )
    description: str = Field(
        description="The degree description, e.g., Doctor of Dental Medicine"
    )
class GeoCode(BaseModel):
    lat: float = Field(
        description="The location latitude"
    )
    lng: float = Field(
        description="The location longitude"
)

class Address (BaseModel):
    address_line_1: Optional [str] = Field(
         description="The first line of the address.",
        default=None
    )
    city: Optional [str] = Field(
        description="The city of the address.",
        default=None
    )
    county: Optional [str] = Field(
        description="The county of the address.",
        default=None
    )
    state_code: Optional [str] = Field(
        description="The state code of the address.",
        default=None
    )
    zip_code: Optional [str] = Field(
        description="The zip code of the address.",
        default=None
    )

    geo_code: Optional [GeoCode] = Field(
        description="The geographical coordinates of the address.",
        default=None
    )

class Provider (BaseModel):
    key: str = Field(
        description="The unique identifier for the provider."
    )
    npi: str = Field(
        description="The National Provider Identifier (NPI) of the provider."
    )

    full_name: str = Field(
        description="The full name of the provider"
    )
    gender: Optional [str] = Field(
        description="The gender of the provider",
        default=None
    )
    degrees: Optional [List [Degree]] = Field(
        description="The degree information of the provider",
        default=None
    )
    virtual_care: Optional [bool] = Field(
        description="Indicates if the provider offers virtual care.",
        default=None
    )
    specialty_description: Optional [List [str]] = Field(
        description="The list of specialty descriptions for the provider.",
        default=None
    )
    address: Optional [Address] = Field(
        description="The address information of the provider.",
        default=None
    )
    web_url: str = Field(
        description="The URL to the provider's detail page.",
        default=None
    )
    distance_in_miles: Optional [float] = Field(
        description="The distance from the search origin to the provider's location in miles.",
        default=None
    )

    @staticmethod
    def from_doc(doc: Mapping [str, Any], base_url: str, origin: Optional [GeoCode]):
        distance_in_miles = None
        
        address = Address(
            address_line_1=doc["address"].get("addressLine1"), city=doc["address"].get("cityName"), county=doc["address"].get("countyName"), zip_code=doc["address"].get("zipCode"),
            state_code=doc["address"].get("stateName"),
            country=doc ["address"].get("countryName"),
            zip_code=doc ["address"].get("zipCode"),
            geo_code=GeoCode(
                lat=doc ["address"] ["geoCode"] ["coordinates"] [1],
                lng=doc ["address"] ["geoCode"] ["coordinates"] [0]
             ) if doc.get("address") and doc["address"].get("geoCode") else None 
        ) if doc.get("address") else None

        if origin is not None and address is not None and address.geo_code is not None:
            distance_in_miles = round(
                great_circle(
                    (origin.lat, origin.lng),
                    (address.geo_code.lat, address.geo_code.lng) 
                ).miles,
                2
            )
        return Provider(
            key=doc ["generatedKey"],
            npi=doc.get("npi") if doc.get("npi") else None, 
            full_name=doc.get("provider", {}).get("fullName"),
            gender=doc.get("provider", {}).get("gender"),
            degrees=[
                Degree(code=item.get("code"), description=item.get("description")) 
                for item in doc.get("degree", [])
            ],
            virtual_care=doc.get("virtualCare", "N").upper() == "Y",
            specialty_description=doc.get("speclDesc"),
            address=address,
            web_url=f"{base_url}/{doc['generatedKey']}",
            distance_in_miles=distance_in_miles
        )

class SearchResult (BaseModel):
    data: List [Provider] = Field(
        description="The list of providers matching the search criteria."
    )

class ChatRequest (BaseModel):
    session_id: str = Field(
        description="The unique identifier for the chat session."
    )
    prompt: str = Field(
        description="The user's prompt."
    )
    lat: float = Field(
        description="The latitude of the search origin"
    )
    lng: float = Field(
        description="The longitude of the search origin"
    )
    network_plan: Optional [str] = Field(
        description="The insurance network plan to search the provider.",
        default=None
    )

class FindByKeyInput (BaseModel):
    key: str = Field(
        description="Unique key to identify a provider"
    )
    lat: float = Field(
        description="The latitude of the search origin"
    )
    lng: float = Field(
        description="The longitude of the search origin"
    )
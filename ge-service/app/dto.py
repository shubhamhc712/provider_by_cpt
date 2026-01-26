from typing import Dict, Optional, List, Any, Mapping
from urllib.parse import urldecode

from geopy.distance import great_circle 
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

def get_primary_specialty(primary_taxonomy: Dict[str, Any]) :
    return None if not primary_taxonomy or not primary_taxonomy.get("taxonomyCodes") else Code(
        code=primary_taxonomy.get("taxonomyCodes"),
        description=primary_taxonomy.get("taxonomyDescription")
    )

def get_distance_in_miles(address, origin):
    if origin is not None and address is not None and address.geo_code is not None:
        distance_in_miles = round(
            great_circle(
                (origin.lat, origin.lng),
                (address.geo_code.lat, address.geo_code.lng)
            ).miles,
            2
        )
    return None

class Code(BaseModel):
    code: str = Field(
        description="The code value."
    )
    description: Optional [str] = Field(
        description="The code description.",
        default=None
    )

class LocationInput(BaseModel):
    lat: Optional[float] = Field(
        description="The latitude for location-based search.",
        default=None
    )
    lng: Optional[float] = Field(
        description="The longitude for location-based search.",
        default=None
    )
    radius_in_meters: float = Field(
        description="The search radius in meters. It will be ignored if lat/lng is not provided.",
        default=48280.3 # 30 miles in meters
    )

    def get_search_origin(self):
        result = None
        if self.lat is not None and self.lng is not None:
            result = GeoCode(lat=self.lat, lng=self.lng)
        return result

class SearchInput (LocationInput):
    cpt_codes: Optional [List [str]] = Field(
        description="The CPT code to search for.Maximum number of CPT codes is 30.",
        default=None,
        max_length=30
    )

    network_ids: List[str] = Field(
        description="The latitude for location-based search.",
        default=[]
    )
    skip: int = Field(
        description="Number of records to skip, for pagination",
        default=0
    )
    limit: int = Field(
        description="Maximum number of results to return. Default is 10. Cant be more than 20.",
        default=10,
        le=20,
        ge=1
    )

    def get_network_ids(self) -> List[str]:
        """
        This will get the network ids. It will parse each entry in the self.network_ids and split by comma.
        :retrun: List of network ids
        """
        original = self.network_ids
        return self.normalize_items(original)
    
    def get_cpt_codes(self) -> List[str]:
        return (item.upper() for item in self.normalize_items(self.cpt_codes))
    
    @staticmethod
    def normalize_iteam(original):
        result: List[str] = []
        if original:
            for item in original:
                parts = [part.strip() for part in item.split(",") if part.strip()]
                result.extend(parts)
        return result

    @model_validator(mode="after")
    def validate_search_input(self) -> Self:
        cpt_codes = self.get_cpt_codes()
        if len(cpt_codes) > 30:
            raise ValueError("Maximum number of CPT codes allowed is 30.")
        return self

class GeoCode(BaseModel):
    lat: float = Field(
        description="The location latitude"
    )
    lng: float = Field(
        description="The location longitude"
    )

    @staticmethod
    def from_doc(doc: Optional [Mapping [str, Any]]) -> Optional["GeoCode"]:
        if doc:
            return GeoCode(
                lat=doc ["coordinates"] [1],
                lng=doc ["coordinates"] [0]
            )
        return None
    
class Phone(BaseModel):
    type: Optional [str] = Field(
        description="The type of phone number (e.g., phone, fax).",
        default=None
    )
    number: Optional [str] = Field(
        description="The phone number.",
        default=None
    )
    confidence: float = Field(
        description="The confidence level of the phone number's accuracy.",
        default=0.0
    )

    @staticmethod
    def from_doc()

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
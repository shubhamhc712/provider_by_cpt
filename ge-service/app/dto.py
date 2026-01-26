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
        return distance_in_miles
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
    def from_doc(doc: Mapping[str, Any]) -> Optional["Phone"]:
        if doc:
            return Phone(
                type=doc.get("type"),
                number=doc.get("number"),
                confidence=doc.get("confidence", 0.0)
            )
        return None
    
class Address (BaseModel):
    display_address: str = Field(
        description="The full display address.",
    )
    geo_code: Optional[GeoCode]= Field(
        description="The geographical coordinates of the address.",
        default=None
    )
    phone: List[Phone] = Field(
        description="The phone numbers with the address.",
        default=[]
    )
    distance_in_miles: Optional [float] = Field(
        description="The distance from origin in miles.",
        default=None
    )

    @staticmethod
    def from_doc(
        doc: Optional[Mapping[str, Any]],
        origin: Optional[GeoCode],
        summary: bool = False
    ) ->Optional["Address"]:
        if doc:
            phones: List[Phone] = [Phone.from_doc(item) for item in doc.get("phones", [])]
            if summary and len(phone) > 0:
                best_phone = phones[0]
                for phone in phones:
                    if phone.type == "phone":
                        if best_phone is None or phone.confidence > best_phone.confidence:
                            best_phone = phone
                phones = [best_phone]

            return Address(
                display_address=doc.get("displayAddress"),
                geo_code=GeoCode.from_doc(doc.get("geoCode")),
                phone=phones,
                distance_in_miles=doc.get("distance")
            )

            return result
        return None
    
class CptInfo(BaseModel):
    code: str = Field(description = "The CPT code.")
    claim_service_start_date: Optional[int] = Field(
        description="Date when the service started, in YYYYMMDD format.",
        default=None
    )
    weight: float = Field(
        description="The weight associated with the CPT code for code the asscoiated provider.",
        default=None
    )
    weight: float = Field(
        description="The weight or relevance scrore of the CPT code for the associated provider.",
    )

class License (BaseModel):
    number: str = Field(
        description="The license number of the provider."
    )
    state: str = Field(
        description="The state where the license is issued."
    )
    eff_dt: str = Field(
        description="The effective date of the license.The format is YYYY-MM-DD."
    )

    exp_dt: str = Field(
        description="Indicates whether the license is voided."
    )

    @staticmethod
    def from_doc(doc: Mapping [str, Any]) :
        return License(
            number=doc.get("licenseNumber"),
            state=doc.get("stateCode"),
            eff_dt=doc.get("effectiveDate"),
            exp_dt=doc.get("expirationDate"),
            voided=doc.get("voidedIndicator") in {"Y", "y"}
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
    addresses: List [Address] = Field(
        description="The addresses of the provider.",
        default=[]
    )
    primary_specialty: Optional [Code] = Field(
        description="The primary specialty of the provider.",
        default=None
    )
    taxonomy_code: List [Code] = Field(
        description="The taxonomy codes of the provider.",
        default=[]
    )

    languages: List[Code] = Field(
        description="The languages spoken by the provider.",
        default=[]
    )
    license: List[License] = Field(
        description="The license of the provider.",
        default=[]
    )
    accept_new_patients: bool = Field(
        description="Indicates if the provider accepts new patients.",
        default=False
    )
    
    accepted_cpts: List [CptInfo] = Field(
        description="The associated CPT codes of the provider.",
        default=[]
    )

    @staticmethod
    def from_doc(doc: Mapping [str, Any], origin: Optional [GeoCode]):
        address = [
            Address.from_doc(iteam ,origin)
            for item in doc.get("addresses", [])
        ]

        taxonomy_codes = [
            Code(
                code=item.get("taxonomycodeDesc"),
                description=item.get("taxonomyDesc")
            ) for item in doc.get("taxonomies", [])
        ]

        primary_taxonomy_doc = doc.get("primary_taxonomy_code")
        primary_specialty = get_primary_specialty(primary_taxonomy_doc)
        doc_languages = doc.get("languages", [])
        languages = []
        if doc_languages:
                if isinstance(doc_languages, str):
                    #Temporary code until the data is fixed
                    languages =[
                        Code(
                            code=doc_languages,
                            description=doc_languages
                        )
                    ]
                else:                  
                    languages = [
                        Code(
                            code=item.get("code"),
                            description=item.get("description")
                        ) for item in doc_languages
                    ]

        doc_licenses = doc.get("licenses", [])
        licenses = []
        if doc_licenses:
            licenses = [
                License.from_doc(item) for item in doc_licenses
            ]
        
        cpt_docs = doc.get("associated_cpts", [])
        if cpt_docs:
            accepted_cpts = [
                CptInfo(
                    code=item.get("code"),
                    claim_service_start_date=item.get("claimServiceStartDate"),
                    weight=item.get("weight", 0.0)
                ) for item in cpt_docs
            ]
        
        else:
            associated_cpts = []

        return Provider(
            key=doc ["ues_enterprise_provider_id"],
            npi=doc.get("npi"),
            full_name=doc.get("display_name"),
            gender=doc.get("gender"),
            addresses=addresses,
            taxonomy_code=taxonomy_codes,
            languages=languages,
            license=licenses,
            primary_specialty=primary_specialty,
            accept_new_patients=doc.get("acceptNewPatients", False),
            associated_cpts=associated_cpts
        )
    
class ProviderSummary (BaseModel):
    key: str = Field(
        description="The unique identifier for the provider."
    )

    name: str = Field(
        description="The name of the provider"
    )

    npi: Optional[str] = Field(
        description="The National Provider Identifier (NPI) of the provider."
    )

    closest_address: Optional[Address] = Field(
        description="The closest address of the provider",
        default=None    
    )
    accept_new_patients: bool = Field(
        description="Indicates if the provider accepts new patients.",
        default=False
    )

    web_url: str = Field(
        description="The web URL of the provider."
    )  

    distance_in_miles: Optional[float] = Field(
        description="The distance from search origin to the provider's location in miles.",
        default=None
    )
    primary_specialty: Optional [Code] = Field(
        description="The primary specialty of the provider.",
        default=None
    )

    @staticmethod
    def from_doc(doc: Mapping [str, Any], base_url: str, param: SearchInput):
        closest_address = Address.from_doc(
            doc.get("closest_address"),
            origin = param.get_search_origin(),
            summary=True
        )
        origin = param.get_search_origin()
        distance_in_miles = get_distance_in_miles(closest_address, origin)
        url_params = ProviderSummary.create_web_url_params(doc, param)
        primary_taxonomy_doc = doc.get("primary_taxonomy_code")
        primary_specialty = get_primary_specialty(primary_taxonomy_doc)
        web_url = f"{base_url}?{urldecode(url_params,doseq=True)}"
        return ProviderSummary(
            key=doc ["ues_enterprise_provider_id"],
            name=doc.get("display_name"),
            npi=doc.get("npi"),
            closest_address=closest_address,
            accept_new_patients=doc.get("acceptNewPatients", False),
            web_url=web_url,
            distance_in_miles=distance_in_miles,
            primary_specialty=primary_specialty
        )
    @staticmethod
    def create_web_url_params(
        doc: Mapping [str, Any],
        param: SearchInput
    ) -> Mapping [str, Any]:
        origin: param.get_search_origin()
        url_params = {
            "key": doc ["ues_enterprise_provider_id"],
            "radius_in_meters": param.radius_in_meters
        }
        if origin:
            url_params["lat"] = origin.lat
            url_params["lng"] = origin.lng
        network_ids = param.get_network_ids()
        if network_ids:
            url_params["network_ids"] = network_ids
        cpt_codes = param.get_cpt_codes()
        if cpt_codes:
            url_params["cpt_codes"] = cpt_codes
        return url_params
    
class SearchResult (BaseModel):
    paginated_data: List [ProviderSummary] = Field(
        description="The paginated list of providers matching the search criteria."
    )
    total_count: int = Field(
        description="The total number of providers matching the search criteria."
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

class FindDetailInput (LocationInput):
    key: str = Field(
        description="Unique key to identify a provider"
    )
    cpt_codes: Optional [List [str]] = Field(
        description="The CPT code to search for.",
        default=None,
    )
    network_ids: List[str] = Field(
        description="The latitude for location-based search.",
        default=[]
    )

class FindByKeyResult (BaseModel):
    data: Optional[Provider] = Field(
        description="The provider details.",
        default=None
    )
    input_param: FindDetailInput = Field(
        description="The input parameters used for the search."
    )

class SearchPlansInput (BaseModel):
    query: Optional [str] = Field(
        description="The search query string.",
        default=None
    )

    skip: int = Field(
        description="Number of records to skip, for pagination. Default is 0.",
        default=0
    )

    limit: int = Field(
        description="Maximum number of results to return. Default is 10.",
        default=10
    )

    def is_query_provided(self) -> bool:
        return self.query is not None and (self.query.strip()) > 0
    
class Plan(BaseModel):
    plaln_name: str = Field(
        description="The name of the insurance plan."
    )
    pes_network_ids: List[str] = Field(
        description="The insurance network IDs associated with the plan.",
        default=[]
    )
    eff_dt: int = Field(
        description="The effective date of the plan information, it will be as int with format YYYYMMDD (e.g., 20251110)."
    )
    exp_dt: int = Field(
        description="The expiration date of the plan information, it will be as int with format YYYYMMDD (e.g., 20251110)."
    )

class SearchPlansResult (BaseModel):
    paginated_data: List [Plan] = Field(
        description="The paginated list of insurance plans matching the search criteria."
    )
    total_count: int = Field(
        description="The total number of insurance plans matching the search criteria."
    )
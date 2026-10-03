from pydantic import BaseModel, Field
from typing import Literal


class PricingReq(BaseModel):
    destination: str = Field(description="The destination of the trip.")
    duration_days: int = Field(description="Number of days for the trip.", gt=0)
    travelers: int = Field(description="Number of travelers.", gt=0)

    accommodation: Literal["budget","mid_range","luxury"] = Field(
        description="Preferred accommodation level."
    )

    transport: Literal["budget","standard","premium"] = Field(
        description="Preferred transportation level."
    )
    
    
class PricingResponse(BaseModel):
    destination: str
    travelers: int
    duration_days: int
    accommodation_cost: float
    transport_cost: float
    food_cost: float
    activities_cost: float

    total_cost: float
    currency: str
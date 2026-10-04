import uuid
from typing import Optional
from pydantic import BaseModel, Field


class TripReq(BaseModel):
    destination: str = Field(min_length=1,description="should be more than on character")
    days: int = Field(ge=1, description="days must be at least more than one")
    budget: float = Field(gt=0,description="value should be a positive number")
    trip_style: str

class TripRes(BaseModel):
    id: uuid.UUID
    destination: str
    days: int
    budget: float
    trip_style: str
    message: Optional[str] = None
    class Config:
        from_attribute = True
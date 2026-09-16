from pydantic import BaseModel, Field


class MapsInput(BaseModel):
    origin: str = Field(description="Starting location.")
    destination: str = Field(description="Destination location.")
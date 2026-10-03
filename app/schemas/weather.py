
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    city: str = Field(description="City name, e.g. 'Kigali'")
    
class WeatherResponse(BaseModel):
    city: str
    country: str
    temperature: float
    wind_speed: float
    weather_code: int
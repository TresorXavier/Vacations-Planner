from pydantic import BaseModel, Field

class RAGInput(BaseModel):
    destination: str = Field(
        description=(
            "The destination to search travel knowledge for, e.g. 'Kigali' "
            "or 'Rwanda'. Must be a real place name "
            "search to the correct country so results aren't pulled from "
            "an unrelated destination with a similar name."
        )
    )
    travel_style: str = Field(description="The trip style, e.g. 'cultural', 'adventure', 'relaxation'.")


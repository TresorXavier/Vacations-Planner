from langchain_core.tools import tool


@tool
def cost_calculation(destination: str,duration_days: int,travelers: int) -> str:
    """Estimate the approximate cost of a trip based on destination, duration and number of travelers."""

    per_person_per_day = 50000
    trip_total = per_person_per_day * duration_days * travelers

    return (
        f"Estimated cost for {travelers} traveler(s), "
        f"{duration_days} days in {destination}: "
        f"approximately $${trip_total:,.0f} total "
        f"(${per_person_per_day} per person per day). "
        f"This is a rough estimate."
    )
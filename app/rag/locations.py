import re

FILE_METADATA_MAP = {
    "hidden_germs.md": {
        "destination": "Kigali", "country": "Rwanda", "continent": "Africa",
        "document_type": "local_tips",
    },
    "destination_notes.md": {
        "destination": "Rwanda", "country": "Rwanda", "continent": "Africa",
        "document_type": "guide",
    },
    "faq.md": {
        "destination": "Rwanda", "country": "Rwanda", "continent": "Africa",
        "document_type": "faq",
    },
    "local_tips.md": {
        "destination": "Rwanda", "country": "Rwanda", "continent": "Africa",
        "document_type": "local_tips",
    },
    "Rwanda - Essential Information for travel.pdf": {
        "destination": "Rwanda", "country": "Rwanda", "continent": "Africa",
        "document_type": "guide",
    },
    "Rwanda_Guidebook_Rewild.pdf": {
        "destination": "Rwanda", "country": "Rwanda", "continent": "Africa",
        "document_type": "guide",
    },
    "DestinationGuide_Japan..pdf": {
        "destination": "Japan", "country": "Japan", "continent": "Asia",
        "document_type": "guide",
    },
}

"""
Files where individual entries may cover different locations within the
same document (e.g. a "hidden gems" list spanning multiple towns). For
these, we try to pull a location out of each entry's own text before
falling back to the file-level destination above."""

MULTI_LOCATION_FILES = {
    "hidden_germs.md",
}

LOCATION_PATTERN = re.compile(r"location\s*:\s*(.+)", re.IGNORECASE)

"""
Raw "Location:" values in source files are inconsistent (slashes, regions,
prose like "Near Akagera National Park"). Chroma's `where` filter is an
exact string match, so these must be normalized to the same canonical
names used elsewhere (trip.destination values, FILE_METADATA_MAP)."""

LOCATION_ALIASES = {
    "kigali": "Kigali",
    "musanze": "Musanze",
    "ruhengeri / musanze region": "Musanze",
    "ruhengeri": "Musanze",
    "nyanza": "Nyanza",
    "huye": "Huye",
    "nyagatare": "Nyagatare",
    "akagera national park": "Akagera",
    "near akagera national park": "Akagera",
    "western rwanda": "Western Province",
    "southern / western rwanda": "Southern Province",
    "southern rwanda": "Southern Province",
}

""" 
Destination-only input means country can't come from the caller -- it has
to be derived. This maps every canonical destination name (the values
LOCATION_ALIASES normalizes to, plus WIKIVOYAGE_SOURCES destinations) to
its country, so retrieve_trip_context can resolve country internally
from destination alone. """
    
DESTINATION_COUNTRY_MAP = {
    "Kigali": "Rwanda",
    "Musanze": "Rwanda",
    "Nyanza": "Rwanda",
    "Huye": "Rwanda",
    "Nyagatare": "Rwanda",
    "Akagera": "Rwanda",
    "Western Province": "Rwanda",
    "Southern Province": "Rwanda",
    "Muhazi": "Rwanda",
    "Nyungwe": "Rwanda",
    "Rwanda": "Rwanda",
    "Kenya": "Kenya",
    "France": "France",
    "Paris": "France",
    "Japan": "Japan",
    "Tokyo": "Japan",
    "United States": "United States",
    "New York City": "United States"
}

WIKIVOYAGE_SOURCES = [
    # --- Africa ---
    {"title": "Rwanda", "continent": "Africa", "country": "Rwanda", "destination": "Rwanda", "document_type": "guide"},
    {"title": "Kigali", "continent": "Africa", "country": "Rwanda", "destination": "Kigali", "document_type": "guide"},
    {"title": "Kenya", "continent": "Africa", "country": "Kenya", "destination": "Kenya", "document_type": "guide"},

    # --- Europe ---
    {"title": "Europe", "continent": "Europe", "country": None, "destination": "Europe", "document_type": "guide"},
    {"title": "France", "continent": "Europe", "country": "France", "destination": "France", "document_type": "guide"},
    {"title": "Paris", "continent": "Europe", "country": "France", "destination": "Paris", "document_type": "guide"},

    # --- Asia ---
    {"title": "Japan", "continent": "Asia", "country": "Japan", "destination": "Japan", "document_type": "guide"},
    {"title": "Tokyo", "continent": "Asia", "country": "Japan", "destination": "Tokyo", "document_type": "guide"},

    # --- America ---
    {"title": "United States of America", "continent": "North America", "country": "United States", "destination": "United States", "document_type": "guide"},
    {"title": "New York City", "continent": "North America", "country": "United States", "destination": "New York City", "document_type": "guide"},
]
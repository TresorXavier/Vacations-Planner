# embed query → filtered similarity search → filter by relevance → return chunks

import logging
import chromadb
from sentence_transformers import SentenceTransformer

from app.rag.locations import DESTINATION_COUNTRY_MAP, LOCATION_ALIASES
from app.rag.parsers_requests import resource_parser_html

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)
chroma_client = chromadb.PersistentClient(path="./chroma_store")
collection = chroma_client.get_or_create_collection(
    name="rwanda_travel",
    metadata={"hnsw:space": "cosine"},
)


def normalize_destination(raw_destination):
    """ Map a trip's raw destination string to the name used in chunk metadata """

    key = raw_destination.strip().lower()
    return LOCATION_ALIASES.get(key, raw_destination.strip())


def resolve_country(normalized_destination):
    """
    Get country from destination alone, since callers only pass
    destination (no separate country field on Trips).
    """
    return DESTINATION_COUNTRY_MAP.get(normalized_destination)


def build_trip_query(destination, country, trip_style):
    """ Building a single semantic query for the whole trip."""
    return f"Things to do and travel tips for {destination}, {country} ({trip_style} style trip)"


def retrieve_trip_context(destination,travel_style,top_k=6,max_distance=0.8):

    normalized_destination = normalize_destination(destination)
    country = resolve_country(normalized_destination)

    if country:

        return retrieve_from_chroma(
            destination=normalized_destination,
            country=country,
            travel_style=travel_style,
            top_k=top_k,
            max_distance=max_distance
        )



    logger.info(
        f"Destination {destination!r} "
        f"is not in local metadata. "
        f"Trying Wikivoyage..."
    )

    elements = resource_parser_html(
        normalized_destination
    )

    if not elements:
        return {
            "chunks": [],
            "used_fallback": True,
            "matched_destination": normalized_destination,
            "matched_country": None,
            "source": "wikivoyage"
        }

    return {
        "chunks": elements,
        "used_fallback": True,
        "matched_destination": normalized_destination,
        "matched_country": None,
        "source": "wikivoyage"
    }
    
    
def retrieve_from_chroma(destination,country,travel_style,top_k=6,max_distance=0.8):

    query_text = build_trip_query(
        destination,
        country,
        travel_style
    )

    query_embedding = model.encode(query_text).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={
            "$and": [
                {"destination": destination},
                {"country": country}
            ]
        }
    )

    used_fallback = False

    if not results["documents"][0]:

        used_fallback = True

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={
                "country": country
            }
        )

    chunks = []

    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):

        if dist > max_distance:
            continue

        chunks.append({
            "text": doc,
            "metadata": meta,
            "distance": dist
        })

    return {
        "chunks": chunks,
        "used_fallback": used_fallback,
        "matched_destination": destination,
        "matched_country": country,
        "source": "chroma"
    }
    
    

def format_context_for_prompt(retrieval_result):
    """ Turn retrieved chunks into a plain-text block for the itinerary prompt """

    chunks = retrieval_result["chunks"]
    if not chunks:
        return "No additional destination context available."
    return "\n\n".join(f"- {c['text']}" for c in chunks)
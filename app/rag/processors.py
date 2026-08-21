from pathlib import Path
import json
import chromadb
from sentence_transformers import SentenceTransformer
from app.rag.locations import (
    FILE_METADATA_MAP,
    LOCATION_ALIASES,
    LOCATION_PATTERN,
    MULTI_LOCATION_FILES,
    WIKIVOYAGE_SOURCES,
)
from app.rag.parsers_requests import resource_parser_html, unstructured_md_parser, unstructured_pdf_parser

""" TODO:
    1.unstructured API call 
    2.layout-aware and chunking 
    3.create embedings
    4.upsert to vector 
"""

resource_docs = Path("resources")
MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)
DROP_CATEGORIES = {"Image", "PageBreak", "Header", "Footer"}
MIN_TEXT_LENGTH = 3
MAX_CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


chroma_client = chromadb.PersistentClient(
    path="./chroma_store"
)
collection = chroma_client.get_or_create_collection(
    name="rwanda_travel",  
    metadata={"hnsw:space": "cosine"},
)


def parse_file_content(file_path):
    """ Read file contentent """

    extension = Path(file_path).suffix.lower()
    if extension == ".pdf":
        return unstructured_pdf_parser(file_path)
    elif extension == ".md":
        return unstructured_md_parser(file_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")


def clean_elements(elements):
    """ Filter out layout-detection noise before chunking/embedding """
    cleaned = []
    for el in elements:
        category = el.get("type", "")
        text = (el.get("text") or "").strip()

        if category in DROP_CATEGORIES:
            continue

        if len(text) < MIN_TEXT_LENGTH:
            continue

        el["text"] = " ".join(text.split())
        cleaned.append(el)

    return cleaned


def normalize_location(raw_location):
    """ Map a raw extracted location string to a destination name """

    key = raw_location.strip().lower()
    return LOCATION_ALIASES.get(key, raw_location.strip())


def extract_location_from_children(children):
    """ Look for a Location style ListItem among a title's children and return the normalized location """

    for child in children:
        text = child.get("text", "")
        text = text.replace("*", "")
        match = LOCATION_PATTERN.search(text)
        if match:
            raw = match.group(1).strip().rstrip(".")
            return normalize_location(raw)
    return None


def build_elements_dicts(elements):
    """
    Shared grouping logic: bucket NarrativeText/ListItem elements under
    their enclosing Title element_id.
    """
    elements_dicts = {}

    for el in elements:
        if el["type"] == "Title":
            elements_dicts[el["element_id"]] = []

    for el in elements:
        if el["type"] in ("NarrativeText", "ListItem"):
            parent = el["metadata"].get("parent_id")
            if parent in elements_dicts:
                elements_dicts[parent].append(el)

    titles = {
        element["element_id"]: element
        for element in elements
        if element["type"] == "Title"
    }

    return elements_dicts, titles


def create_chunks(elements, filename):
    """
    Local-file chunker. Group content elements under their enclosing Title,
    split oversized groups, and attach metadata (filename, destination,
    country, continent, document_type, section, element_id, chunk_index)
    to every resulting chunk. `filename` must be a string key into
    FILE_METADATA_MAP.
    """
    elements_dicts, titles = build_elements_dicts(elements)

    file_meta = FILE_METADATA_MAP.get(filename, {})
    file_destination = file_meta.get("destination", "Unknown")
    country = file_meta.get("country", "Unknown")
    continent = file_meta.get("continent", "Unknown")
    document_type = file_meta.get("document_type", "unknown")
    is_multi_location = filename in MULTI_LOCATION_FILES

    all_chunks = []

    for title_id, children in elements_dicts.items():
        title = titles.get(title_id)
        if not title:
            continue

        title_text = title.get("text", "").strip()

        if is_multi_location:
            destination = extract_location_from_children(children) or file_destination
        else:
            destination = file_destination

        text_chunks = split_title_children(title_text, children)

        for i, chunk_text in enumerate(text_chunks):
            all_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "filename": filename,
                    "destination": destination,
                    "country": country,
                    "continent": continent,
                    "document_type": document_type,
                    "source": "local_file",
                    "section": title_text,
                    "element_id": f"{title_id}_{i}",
                    "chunk_index": i,
                }
            })

    return all_chunks


def create_chunks_from_source(elements, source):
    """ Web-source (Wikivoyage) chunker but metadata comes directly from a source """
    elements_dicts, titles = build_elements_dicts(elements)

    all_chunks = []

    for title_id, children in elements_dicts.items():
        title = titles.get(title_id)
        if not title:
            continue

        title_text = title.get("text", "").strip()
        text_chunks = split_title_children(title_text, children)

        for i, chunk_text in enumerate(text_chunks):
            all_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "filename": f"wikivoyage:{source['title']}",
                    "destination": source["destination"],
                    "country": source["country"],
                    "continent": source["continent"],
                    "document_type": source["document_type"],
                    "source": "wikivoyage",
                    "section": title_text,
                    "element_id": f"wikivoyage_{source['title']}_{title_id}_{i}",
                    "chunk_index": i,
                }
            })

    return all_chunks


def split_title_children(title_text, children):
    """
    Given a Title's text and its child elements (raw dicts with 'text' keys),
    return a list of plain-text chunk strings, each stays near MAX_CHUNK_SIZE,
    each re-prefixed with the title so every chunk stays self-contained.
    """
    chunks = []
    current_parts = [title_text]
    current_length = len(title_text)

    for child in children:
        child_text = child.get("text", "").strip()

        if not child_text:
            continue

        additional_length = len(child_text) + 2

        if current_length + additional_length > MAX_CHUNK_SIZE and len(current_parts) > 1:
            chunks.append("\n\n".join(current_parts))
            overlap_parts = []
            overlap_length = 0
            
            for part in reversed(current_parts[1:]):
                part_len = len(part) + 2
                if overlap_length + part_len > CHUNK_OVERLAP:
                    break
                overlap_parts.insert(0, part)
                overlap_length += part_len
                
            current_parts = [title_text, child_text]
            current_length = len(title_text) + additional_length
        else:
            current_parts.append(child_text)
            current_length += additional_length

    if len(current_parts) > 1:
        chunks.append("\n\n".join(current_parts))

    return chunks


def embed_and_store(chunks, collection, model):
    """ Create embeding and store them in chromadb """

    ids = []
    documents = []
    metadatas = []
    embeddings = []

    for chunk in chunks:
        ids.append(chunk["metadata"]["element_id"])
        documents.append(chunk["text"])
        metadatas.append(chunk["metadata"])
        embeddings.append(model.encode(chunk["text"]).tolist())

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )


def fetch_resource_from_wiki():
    """ Get all elements from Wikivoyage sources and ingest them. """
    
    for source in WIKIVOYAGE_SOURCES:
        print(f"Fetching Wikivoyage: {source['title']} ({source['destination']})")

        elements = resource_parser_html(source["title"])
        if not elements:
            print(f"  skipped -- no content returned for {source['title']!r}")
            continue

        elements = clean_elements(elements)
        chunks = create_chunks_from_source(elements, source) 

        output_file = f"output_wikivoyage_{source['title'].replace(' ', '_')}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)

        embed_and_store(chunks, collection, model)
        print(f"  stored {len(chunks)} chunks")


def ingestion_pipeline():
    for file in resource_docs.rglob("*"):
        if not file.is_file():
            continue

        elements = parse_file_content(file)
        elements = clean_elements(elements)
        chunks = create_chunks(elements, file.name)
        embed_and_store(chunks, collection, model)


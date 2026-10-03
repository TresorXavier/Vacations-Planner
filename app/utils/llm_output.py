import json
import re


def extract_json_content(raw: str) -> dict:
    """Extract the JSON object from a model response.

    1. Look for a ```json ... ``` block.
    2. Otherwise take the outermost { ... }.
    3. Otherwise try to parse the whole text.
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        braced = re.search(r"(\{.*\})", raw, re.DOTALL)
        candidate = braced.group(1) if braced else raw.strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Could not parse model output as JSON: {e}\nExtracted: {candidate[:500]!r}"
        )


def extract_text(content) -> str:
    """Get plain text from a message chunk (string or list of blocks)."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)

    return ""
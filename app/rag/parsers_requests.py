import json
import requests
from unstructured.partition.html import partition_html
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured.staging.base import dict_to_elements
from unstructured_client.models.errors import SDKError
from unstructured.partition.md import partition_md

from app.core.config import settings


client = UnstructuredClient(api_key_auth=settings.UNSTRUCTURED_API)
WIKI_API_BASE = settings.WIKI_API_BASE
USER_AGENT = settings.USER_AGENT
 

def fetch_resource_html(title):
    url = f"{WIKI_API_BASE}/{title.replace(' ', '_')}"
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Failed to fetch resource page {title!r}: {e}")
        return None
 
 
def resource_parser_html(title):

    html = fetch_resource_html(title)
    if html is None:
        return []
 
    elements = partition_html(text=html)
    return [el.to_dict() for el in elements]


def unstructured_pdf_parser(file_path):

    try:
        with open(file_path, "rb") as file:

            request = operations.PartitionRequest(
                partition_parameters=shared.PartitionParameters(
                    files=shared.Files(
                        content=file,
                        file_name=str(file_path)
                    ),
                    strategy="hi_res",
                    hi_res_model_name="yolox",
                )
            )

            response = client.general.partition(request=request)

        elements =  dict_to_elements(response.elements)
        return [ el.to_dict() for el in elements]

    except SDKError as e:
        print(e)
        return []

def unstructured_md_parser(file_path):
    elements = partition_md(filename=str(file_path))

    element_dict = [
        element.to_dict()
        for element in elements
    ]
    return element_dict


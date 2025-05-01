"""
FastAPI endpoints for the RCAccelerator API.
"""
import asyncio
from typing import Dict, Any, List
import re
import httpx
from httpx_gssapi import HTTPSPNEGOAuth, OPTIONAL
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, HttpUrl
from constants import CI_LOGS_PROFILE, DOCS_PROFILE, RCA_FULL_PROFILE
from chat import handle_user_message_api
from config import config
from settings import ModelSettings
from generation import discover_generative_model_names
from embeddings import discover_embeddings_model_names

app = FastAPI(title="RCAccelerator API")

class ChatRequest(BaseModel):
    """
    Represents the parameters for a chat request, including
    message content, similarity threshold, temperature, and max token limit.
    """
    content: str
    similarity_threshold: float = Field(
        config.search_similarity_threshold,
        ge=-1.0,
        le=1.0
        )
    temperature: float = Field(
        config.default_temperature,
        ge=0.0,
        le=1.0
    )
    max_tokens: int = Field(
        config.default_max_tokens,
        gt=1,
        le=1024
    )
    generative_model_name: str = Field(
        config.generative_model,
        description="The name of the generative model to use."
    )
    embeddings_model_name: str = Field(
        config.embeddings_model,
        description="The name of the embeddings model to use."
    )
    profile_name: str = Field(
        CI_LOGS_PROFILE,
        description="The name of the profile to use."
    )

    @field_validator('generative_model_name', mode='after')
    @classmethod
    def validate_generative_model_name(cls, value: str) -> str:
        """Validate the generative model name."""
        available_generative_models = discover_generative_model_names()
        if value not in available_generative_models:
            raise ValueError("Invalid generative model name. Available models are: " +
                             f"{available_generative_models}")
        return value

    @field_validator('embeddings_model_name', mode='after')
    @classmethod
    def validate_embeddings_model_name(cls, value: str) -> str:
        """Validate the embeddings model name."""
        available_embeddings_models = discover_embeddings_model_names()
        if value not in available_embeddings_models:
            raise ValueError("Invalid embeddings model name. Available models are: " +
                             f"{available_embeddings_models}")
        return value

    @field_validator('profile_name', mode='after')
    @classmethod
    def validate_product_name(cls, value: str) -> str:
        """Validate the product name."""
        if value not in [CI_LOGS_PROFILE, DOCS_PROFILE, RCA_FULL_PROFILE]:
            raise ValueError("Invalid profile name. Available profiles are: " +
                             f"{[CI_LOGS_PROFILE, DOCS_PROFILE, RCA_FULL_PROFILE]}.")
        return value


class RcaRequest(BaseModel):
    """Request model for the RCA endpoint."""
    tempest_report_url: HttpUrl = Field(..., description="URL of the Tempest report HTML file.")


class RcaResponseItem(BaseModel):
    """Response item for a single RCA."""
    test_name: str
    response: str
    urls: List[str]


def _extract_test_name(test_name_part: str) -> str:
    """Extract the test name from the text before the traceback."""
    # Extract the test name using a regex pattern
    test_name_match = re.search(r'ft\d+\.\d+:\s*(.*?)\)?testtools', test_name_part)
    if test_name_match:
        test_name = test_name_match.group(1).strip()
        if test_name.endswith('('):
            test_name = test_name[:-1].strip()
    else:
        # Try alternative pattern for different formats
        test_name_match = re.search(r'ft\d+\.\d+:\s*(.*?)$', test_name_part)
        if test_name_match:
            test_name = test_name_match.group(1).strip()
        else:
            test_name = "Unknown Test Name"

    # Remove any content within square brackets
    # e.g. test_tagged_boot_devices[id-a2e65a6c,image,network,slow,volume]
    # becomes test_tagged_boot_devices
    test_name = re.sub(r'\[.*?\]', '', test_name).strip()

    # Remove any content within parentheses
    test_name = re.sub(r'\(.*?\)', '', test_name).strip()

    return test_name


async def fetch_and_parse_tempest_report(url: str) -> List[Dict[str, str]]:
    """Fetches and parses the Tempest HTML report to extract test names and tracebacks."""
    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        try:
            response = await client.get(url, auth=HTTPSPNEGOAuth(mutual_authentication=OPTIONAL))
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=400, detail=f"Error fetching URL: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code,
                                detail=f"Error response {exc.response.status_code} " +
                                f"while requesting {exc.request.url!r}.") from exc

    soup = BeautifulSoup(response.text, 'html.parser')
    failed_test_rows = soup.find_all('tr', id=re.compile(r'^ft\d+\.\d+'))

    results = []
    for row in failed_test_rows:
        row_text = row.get_text().strip()

        traceback_start_marker = "Traceback (most recent call last):"
        traceback_start_index = row_text.find(traceback_start_marker)

        if traceback_start_index != -1:
            test_name_part = row_text[:traceback_start_index].strip()
            test_name = _extract_test_name(test_name_part)

            traceback_text = row_text[traceback_start_index:]
            end_marker_index = traceback_text.find("}}}")
            if end_marker_index != -1:
                traceback_text = traceback_text[:end_marker_index].strip()
            else:
                traceback_text = traceback_text.strip()

            results.append({"test_name": test_name, "traceback": traceback_text})

    if not results:
        pass

    return results


@app.post("/prompt")
async def process_prompt(message_data: ChatRequest) -> Dict[str, Any]:
    """
    FastAPI endpoint that processes a message and returns an answer.
    """
    generative_model_settings: ModelSettings = {
        "model": message_data.generative_model_name,
        "max_tokens": message_data.max_tokens,
        "temperature": message_data.temperature,
    }
    embeddings_model_settings: ModelSettings = {
        "model": message_data.embeddings_model_name,
    }

    response = await handle_user_message_api(
        message_data.content,
        message_data.similarity_threshold,
        generative_model_settings,
        embeddings_model_settings,
        message_data.profile_name,
        )

    return  {
        "response": getattr(response, "content", ""),
        "urls": getattr(response, "urls", [])
    }


@app.post("/rca-from-tempest", response_model=List[RcaResponseItem])
async def process_rca(request: RcaRequest) -> List[RcaResponseItem]:
    """
    FastAPI endpoint that extracts Root Cause Analyses (RCAs) from a Tempest report URL.
    """
    traceback_items = await fetch_and_parse_tempest_report(str(request.tempest_report_url))

    if not traceback_items:
        raise HTTPException(status_code=404, detail="No tracebacks found in " +
                            "the provided Tempest report URL.")

    default_chat_request = ChatRequest(content="")
    generative_model_settings: ModelSettings = {
        "model": default_chat_request.generative_model_name,
        "max_tokens": default_chat_request.max_tokens,
        "temperature": default_chat_request.temperature,
    }
    embeddings_model_settings: ModelSettings = {
        "model": default_chat_request.embeddings_model_name,
    }
    similarity_threshold = default_chat_request.similarity_threshold
    profile_name = default_chat_request.profile_name

    unique_items = {}
    for item in traceback_items:
        # If we've seen this test name before, skip it
        if item['test_name'] not in unique_items:
            unique_items[item['test_name']] = item

    tasks = []
    for test_name, item in unique_items.items():
        message = f"Test: {test_name}\n\n{item['traceback']}"
        task = handle_user_message_api(
            message_content=message,
            similarity_threshold=similarity_threshold,
            generative_model_settings=generative_model_settings,
            embeddings_model_settings=embeddings_model_settings,
            profile_name=profile_name,
        )
        tasks.append((test_name, task))

    raw_results = await asyncio.gather(*[task for _, task in tasks])

    response_list = [
        RcaResponseItem(
            test_name=test_name,
            response=getattr(res, "content", "Error generating RCA."),
            urls=getattr(res, "urls", [])
        )
        for (test_name, res) in zip([t[0] for t in tasks], raw_results)
    ]

    return response_list

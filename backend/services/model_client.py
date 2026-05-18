"""HTTP client for the separate face model service."""

from __future__ import annotations

import os
from typing import Any

import httpx


def get_model_service_url() -> str:
    return os.getenv("MODEL_SERVICE_URL", "http://localhost:8001").rstrip("/")


def get_model_service_token() -> str | None:
    token = os.getenv("MODEL_SERVICE_TOKEN")
    return token if token else None


async def extract_embedding(content: bytes, filename: str | None = None) -> dict[str, Any]:
    """Send an image to the model service and return its JSON payload."""
    url = f"{get_model_service_url()}/embed"
    files = {"photo": (filename or "image.jpg", content, "application/octet-stream")}
    headers = {}
    token = get_model_service_token()
    if token:
        headers["X-Model-Service-Token"] = token

    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, files=files, headers=headers)
        response.raise_for_status()
        return response.json()

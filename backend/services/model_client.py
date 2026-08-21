"""HTTP client for the separate face model service."""

from __future__ import annotations

import os
from typing import Any

import httpx


def get_model_service_url() -> str:
    return os.getenv("MODEL_SERVICE_URL", "http://localhost:8001").rstrip("/")


async def extract_embedding(content: bytes, filename: str | None = None) -> dict[str, Any]:
    """Send an image to the model service and return its JSON payload."""
    url = f"{get_model_service_url()}/embed"
    files = {"photo": (filename or "image.jpg", content, "application/octet-stream")}

    timeout = httpx.Timeout(120.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, files=files)
        if response.status_code >= 400:
            detail = response.text
            try:
                detail_json = response.json()
                if isinstance(detail_json, dict):
                    detail = detail_json.get("detail") or detail_json.get("message") or detail
            except Exception:
                pass
            raise RuntimeError(
                f"Model service returned {response.status_code}: {detail}"
            )
        return response.json()

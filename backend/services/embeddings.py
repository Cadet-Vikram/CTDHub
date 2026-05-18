"""Embedding helpers for cosine matching."""

from __future__ import annotations

import json
import math
from typing import Iterable, Sequence


def from_json_embedding(raw: str) -> list[float]:
    return [float(x) for x in json.loads(raw)]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0

    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y

    denom = math.sqrt(norm_a) * math.sqrt(norm_b)
    if denom <= 1e-12:
        return 0.0
    return dot / denom


def search_matches(
    query: Sequence[float],
    database: Iterable[tuple[str, Sequence[float]]],
    threshold: float = 0.60,
    top_k: int = 5,
) -> list[dict]:
    scores = []
    for child_id, embedding in database:
        similarity = cosine_similarity(query, embedding)
        scores.append(
            {
                "child_id": child_id,
                "similarity": similarity,
                "confidence": similarity * 100.0,
            }
        )

    scores.sort(key=lambda item: item["similarity"], reverse=True)
    return [item for item in scores[:top_k] if item["similarity"] >= threshold]

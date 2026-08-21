"""Face Search route"""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Child, SearchLog, get_db
from services.embeddings import from_json_embedding, search_matches
from services.model_client import extract_embedding

router = APIRouter()
UPLOAD_DIR = "uploads/searches"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/face")
async def search_by_face(
    photo: UploadFile = File(...),
    location_lat: Optional[float] = Form(None),
    location_lng: Optional[float] = Form(None),
    searched_by: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    content = await photo.read()

    try:
        model_result = await extract_embedding(content, photo.filename)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Model service unavailable: {exc}") from exc

    query_embedding = model_result.get("embedding")
    face_count = int(model_result.get("face_count") or 0)
    if query_embedding is None:
        return {
            "matches": [],
            "face_count": face_count,
            "message": "No face detected in the provided image",
        }

    query_id = str(uuid.uuid4())
    query_path = os.path.join(UPLOAD_DIR, f"{query_id}.jpg").replace("\\", "/")
    with open(query_path, "wb") as f:
        f.write(content)

    result = await db.execute(
        select(Child).where(
            Child.face_embedding.isnot(None),
            Child.status == "missing",
        )
    )
    children = result.scalars().all()

    database = []
    for c in children:
        try:
            database.append((c.id, from_json_embedding(c.face_embedding)))
        except Exception:
            pass

    matches = search_matches(query_embedding, database, threshold=0.60)

    enriched = []
    child_map = {c.id: c for c in children}
    for m in matches:
        c = child_map.get(m["child_id"])
        if c:
            enriched.append(
                {
                    "child_id": c.id,
                    "name": c.name,
                    "age": c.age,
                    "gender": c.gender,
                    "similarity": round(m["similarity"], 4),
                    "confidence_percent": round(m["confidence"], 1),
                    "last_seen_location": c.last_seen_location,
                    "contact_number": c.contact_number,
                    "photo_path": c.photo_path,
                }
            )

    best = enriched[0] if enriched else None
    log = SearchLog(
        query_photo_path=query_path,
        matched_child_id=best["child_id"] if best else None,
        similarity_score=best["similarity"] if best else None,
        searched_by=searched_by,
        location_lat=location_lat,
        location_lng=location_lng,
    )
    db.add(log)
    await db.commit()

    return {
        "matches": enriched,
        "face_count": face_count,
        "search_id": query_id,
        "message": f"Found {len(enriched)} potential match(es)",
    }

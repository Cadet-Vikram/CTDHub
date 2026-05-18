"""Face Search route"""

import os
import uuid
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Child, SearchLog, get_db

router = APIRouter()
UPLOAD_DIR = "uploads/searches"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _decode_image(content: bytes):
    try:
        import cv2
        arr = np.frombuffer(content, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        try:
            import io
            from PIL import Image
            img = Image.open(io.BytesIO(content)).convert("RGB")
            return np.array(img)[:, :, ::-1]
        except Exception:
            return None


@router.post("/face")
async def search_by_face(
    request:    Request,
    photo:      UploadFile      = File(...),
    location_lat: Optional[float] = Form(None),
    location_lng: Optional[float] = Form(None),
    searched_by:  Optional[str]   = Form(None),
    db: AsyncSession = Depends(get_db),
):
    content = await photo.read()
    image   = _decode_image(content)
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    face_model = getattr(request.app.state, "face_model", None)
    if face_model is None:
        raise HTTPException(status_code=503, detail="Face model not ready")

    query_embedding, faces = face_model.process_image(image)
    if query_embedding is None:
        return {"matches": [], "face_count": 0,
                "message": "No face detected in the provided image"}

    # Save query photo
    query_id   = str(uuid.uuid4())
    query_path = os.path.join(UPLOAD_DIR, f"{query_id}.jpg").replace("\\", "/")
    with open(query_path, "wb") as f:
        f.write(content)

    # Load all embeddings from DB
    result   = await db.execute(
        select(Child).where(
            Child.face_embedding.isnot(None),
            Child.status == "missing",
        )
    )
    children = result.scalars().all()

    database = []
    for c in children:
        try:
            emb = face_model.from_json(c.face_embedding)
            database.append((c.id, emb))
        except Exception:
            pass

    matches = face_model.search(query_embedding, database, threshold=0.60)

    # Enrich with child details
    enriched = []
    child_map = {c.id: c for c in children}
    for m in matches:
        c = child_map.get(m["child_id"])
        if c:
            enriched.append({
                "child_id":           c.id,
                "name":               c.name,
                "age":                c.age,
                "gender":             c.gender,
                "similarity":         round(m["similarity"], 4),
                "confidence_percent": round(m["confidence"], 1),
                "last_seen_location": c.last_seen_location,
                "contact_number":     c.contact_number,
                "photo_path":         c.photo_path,
            })

    # Log
    best = enriched[0] if enriched else None
    log = SearchLog(
        query_photo_path = query_path,
        matched_child_id = best["child_id"] if best else None,
        similarity_score = best["similarity"] if best else None,
        searched_by      = searched_by,
        location_lat     = location_lat,
        location_lng     = location_lng,
    )
    db.add(log)
    await db.commit()

    return {
        "matches":    enriched,
        "face_count": len(faces),
        "search_id":  query_id,
        "message":    f"Found {len(enriched)} potential match(es)",
    }

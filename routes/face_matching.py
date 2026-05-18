"""
Face Matching Routes
POST /api/face/search  - Search uploaded photo against missing-children DB
POST /api/face/enroll  - Enroll a new face embedding for a case
"""

import io
import json
import uuid
import logging
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from utils.database import get_db, ChildRecord
from utils.face_engine import (
    load_image_from_bytes,
    extract_embedding,
    match_face,
    detect_faces_mtcnn,
    enhance_image,
)
from utils.alert_system import send_match_found_alert

router = APIRouter()
logger = logging.getLogger(__name__)


async def _load_all_embeddings(db: AsyncSession):
    """Fetch all enrolled face embeddings from DB."""
    result = await db.execute(
        select(ChildRecord).where(
            ChildRecord.face_embedding != None,
            ChildRecord.status == "missing",
        )
    )
    children = result.scalars().all()
    pairs = []
    for c in children:
        emb = c.get_embedding()
        if emb:
            pairs.append((c.case_id, np.array(emb, dtype=np.float32)))
    return pairs, {c.case_id: c for c in children}


@router.post("/search")
async def search_face(
    photo: UploadFile = File(...),
    lat: float = Form(default=None),
    lon: float = Form(default=None),
    reporter_name: str = Form(default="Anonymous"),
    reporter_phone: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a photo and search for matching missing children.
    Returns ranked list of potential matches.
    """
    data = await photo.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 10 MB)")

    image = load_image_from_bytes(data)
    if image is None:
        raise HTTPException(400, "Could not decode image")

    image = enhance_image(image)
    faces = detect_faces_mtcnn(image)
    if not faces:
        return JSONResponse({"matched": False, "message": "No face detected in image", "results": []})

    query_emb = extract_embedding(image)
    if query_emb is None:
        raise HTTPException(500, "Could not extract face embedding")

    candidates, child_map = await _load_all_embeddings(db)
    if not candidates:
        return JSONResponse({"matched": False, "message": "No enrolled faces in database", "results": []})

    matches = match_face(query_emb, candidates)
    results = []
    for case_id, score in matches[:5]:
        child = child_map.get(case_id)
        if child:
            results.append({
                "case_id": case_id,
                "name": child.name,
                "age": child.age_at_disappearance,
                "missing_since": str(child.missing_since),
                "last_seen_location": child.last_seen_location,
                "similarity": round(score, 4),
                "confidence_pct": int(score * 100),
                "photo": child.photo_path,
            })

    if results:
        top = results[0]
        top_child = child_map.get(top["case_id"])
        if top_child and top["similarity"] >= 0.75:
            sighting = {"sighting_location": f"{lat},{lon}" if lat else "Unknown"}
            send_match_found_alert(
                {"name": top_child.name, "case_id": top_child.case_id,
                 "guardian_phone": top_child.guardian_phone},
                sighting,
                top["similarity"],
            )

    return {
        "matched": len(results) > 0,
        "faces_detected": len(faces),
        "total_results": len(results),
        "results": results,
    }


@router.post("/enroll/{case_id}")
async def enroll_face(
    case_id: str,
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Enroll or update the face embedding for a case."""
    result = await db.execute(select(ChildRecord).where(ChildRecord.case_id == case_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(404, f"Case {case_id} not found")

    data = await photo.read()
    image = load_image_from_bytes(data)
    if image is None:
        raise HTTPException(400, "Cannot decode image")

    embedding = extract_embedding(image)
    if embedding is None:
        raise HTTPException(422, "No face detected in enrollment photo")

    child.set_embedding(embedding.tolist())

    # Save photo
    photo_name = f"{case_id}_{uuid.uuid4().hex[:8]}.jpg"
    import cv2, os
    os.makedirs("uploads/children", exist_ok=True)
    photo_path = f"uploads/children/{photo_name}"
    cv2.imwrite(photo_path, image)
    child.photo_path = photo_path

    await db.commit()
    return {"status": "enrolled", "case_id": case_id, "embedding_dim": len(embedding)}


@router.get("/stats")
async def face_stats(db: AsyncSession = Depends(get_db)):
    """Return DB enrollment stats."""
    result = await db.execute(select(ChildRecord))
    all_children = result.scalars().all()
    enrolled = [c for c in all_children if c.face_embedding]
    return {
        "total_cases": len(all_children),
        "enrolled_with_face": len(enrolled),
        "missing": len([c for c in all_children if c.status == "missing"]),
        "found": len([c for c in all_children if c.status == "found"]),
    }

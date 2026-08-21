"""
Search & Face Matching API
- Upload photo → detect face → extract embedding → match against DB
- Returns ranked list of potential matches with confidence scores
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

from app.database import get_db
from app.models.child import Child
from app.models.alert import Alert

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/face")
async def search_by_face(
    request: Request,
    image: UploadFile = File(...),
    search_radius_km: float = Form(50.0),
    location_lat: float = Form(None),
    location_lng: float = Form(None),
    top_k: int = Form(5),
    db: AsyncSession = Depends(get_db),
):
    """
    Main search endpoint.
    Upload a photo of a found/spotted child → system matches against all missing children.

    Steps:
    1. Detect face in uploaded image (MTCNN)
    2. Extract 512-dim embedding (ArcFace)
    3. Cosine similarity against all DB embeddings
    4. Return ranked matches with confidence
    5. Auto-trigger alert if confidence > 80%
    """
    image_bytes = await image.read()
    face_service = request.app.state.face_service

    # Step 1: Detect faces
    faces = face_service.detect_faces(image_bytes)
    if not faces:
        return {
            "success": False,
            "error": "No face detected in image",
            "matches": [],
            "faces_detected": 0,
        }

    # Step 2: Extract embedding
    embedding = face_service.extract_embedding(image_bytes)
    if embedding is None:
        return {
            "success": False,
            "error": "Could not extract facial features",
            "matches": [],
            "faces_detected": len(faces),
        }

    # Step 3: Load all missing children with embeddings
    query = select(Child).where(
        Child.status == "missing",
        Child.has_biometrics == True,
        Child.face_embedding != None,
    )
    result = await db.execute(query)
    db_children = result.scalars().all()

    if not db_children:
        return {
            "success": True,
            "matches": [],
            "faces_detected": len(faces),
            "message": "No registered missing children with biometrics in database",
        }

    # Step 4: Match
    records = [c.to_dict() for c in db_children]
    # Include face_embedding in records for matching
    for i, c in enumerate(db_children):
        records[i]["face_embedding"] = c.face_embedding

    matches = face_service.match_against_database(embedding, records, top_k=top_k)

    # Step 5: Auto-alert on high confidence
    high_confidence_matches = [m for m in matches if m["similarity"] >= 80.0]
    alerts_triggered = []
    for match in high_confidence_matches:
        alert_service = request.app.state.alert_service
        alert = await alert_service.send_match_alert(
            child_id=match["child_id"],
            child_name=match["child_name"],
            confidence=match["similarity"],
            match_location=f"{location_lat or 0:.4f},{location_lng or 0:.4f}",
            guardian_phone="",  # Fetch from DB in production
            officer_phones=[],
        )
        alerts_triggered.append(match["child_id"])

    return {
        "success": True,
        "faces_detected": len(faces),
        "embedding_dims": len(embedding),
        "matches": matches,
        "high_confidence_matches": len(high_confidence_matches),
        "alerts_triggered": alerts_triggered,
        "search_radius_km": search_radius_km,
    }


@router.post("/description")
async def search_by_description(
    gender: str = Form(None),
    age_min: int = Form(None),
    age_max: int = Form(None),
    eye_color: str = Form(None),
    hair_color: str = Form(None),
    skin_tone: str = Form(None),
    last_seen_location: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Search missing children by physical description (no photo needed)"""
    query = select(Child).where(Child.status == "missing")

    result = await db.execute(query)
    all_children = result.scalars().all()

    # Filter by description
    filtered = []
    for c in all_children:
        score = 0
        if gender and c.gender and c.gender.lower() == gender.lower():
            score += 2
        if age_min is not None and c.age >= age_min:
            score += 1
        if age_max is not None and c.age <= age_max:
            score += 1
        if eye_color and c.eye_color and eye_color.lower() in c.eye_color.lower():
            score += 2
        if hair_color and c.hair_color and hair_color.lower() in c.hair_color.lower():
            score += 2
        if skin_tone and c.skin_tone and skin_tone.lower() in c.skin_tone.lower():
            score += 1
        if last_seen_location and c.last_seen_location and last_seen_location.lower() in c.last_seen_location.lower():
            score += 3

        if score > 0:
            d = c.to_dict()
            d["match_score"] = score
            filtered.append(d)

    filtered.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "success": True,
        "total_matches": len(filtered),
        "results": filtered[:20],
    }


@router.get("/stats")
async def get_search_stats(db: AsyncSession = Depends(get_db)):
    """Dashboard statistics"""
    result_missing = await db.execute(select(Child).where(Child.status == "missing"))
    result_found = await db.execute(select(Child).where(Child.status == "found"))
    result_alerts = await db.execute(select(Alert))

    missing = result_missing.scalars().all()
    found = result_found.scalars().all()
    alerts = result_alerts.scalars().all()

    return {
        "total_missing": len(missing),
        "total_found": len(found),
        "total_alerts": len(alerts),
        "with_biometrics": sum(1 for c in missing if c.has_biometrics),
        "under_5": sum(1 for c in missing if c.too_young_for_biometrics),
        "aadhaar_verified": sum(1 for c in missing if c.aadhaar_verified),
        "recovery_rate": round(len(found) / max(len(missing) + len(found), 1) * 100, 1),
    }

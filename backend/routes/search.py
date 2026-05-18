"""
/api/search — Upload a photo and match against all open cases.
This is the core "have you seen this child?" API endpoint.
"""
import io
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from PIL import Image

from services.face_recognition import FaceRecognitionService
from routes.cases import CASES   # shared in-memory store

router = APIRouter()


class MatchResult(BaseModel):
    case_id: int
    case_number: str
    child_name: str
    similarity: float
    is_match: bool
    status: str
    guardian_phone: str
    last_seen_location: str
    photo_url: Optional[str]


@router.post("/face-match", response_model=list[MatchResult])
async def face_match(
    photo: UploadFile = File(...),
    top_k: int = Form(5),
):
    """
    Upload a photo (sighting / CCTV frame / etc.).
    Returns top-K matching cases sorted by similarity.
    """
    face_svc = FaceRecognitionService()

    img_bytes = await photo.read()
    image = Image.open(io.BytesIO(img_bytes))
    query_embedding = face_svc.detect_and_embed(image)

    if query_embedding is None:
        raise HTTPException(status_code=422, detail="No face detected in the uploaded image.")

    # Build DB embedding list from open cases that have embeddings
    db_entries = [
        {
            "case_id": c["id"],
            "embedding_bytes": c["embedding_bytes"],
            "age_at_missing": c["age_at_missing"],
        }
        for c in CASES.values()
        if c.get("embedding_bytes") and c["status"] == "open"
    ]

    if not db_entries:
        return []

    matches = face_svc.match_against_database(query_embedding, db_entries, top_k=top_k)

    results = []
    for m in matches:
        case = CASES.get(m["case_id"])
        if not case:
            continue
        results.append(MatchResult(
            case_id=case["id"],
            case_number=case["case_number"],
            child_name=case["child_name"],
            similarity=m["similarity"],
            is_match=m["is_match"],
            status=case["status"],
            guardian_phone=case["guardian_phone"],
            last_seen_location=case["last_seen_location"],
            photo_url=case.get("photo_url"),
        ))
    return results


@router.post("/quick-sos-match")
async def quick_sos_match(
    photo: UploadFile = File(...),
    reporter_lat: float = Form(0.0),
    reporter_lng: float = Form(0.0),
):
    """
    Lightweight version for SOS button — only checks cases within geo radius.
    Returns best match + guardian contact if similarity > threshold.
    """
    face_svc = FaceRecognitionService()
    img_bytes = await photo.read()
    image = Image.open(io.BytesIO(img_bytes))
    query_embedding = face_svc.detect_and_embed(image)

    if query_embedding is None:
        return {"matched": False, "reason": "no_face_detected"}

    db_entries = [
        {"case_id": c["id"], "embedding_bytes": c["embedding_bytes"], "age_at_missing": c["age_at_missing"]}
        for c in CASES.values()
        if c.get("embedding_bytes") and c["status"] == "open"
    ]

    if not db_entries:
        return {"matched": False, "reason": "no_cases_in_db"}

    matches = face_svc.match_against_database(query_embedding, db_entries, top_k=1)
    if not matches or not matches[0]["is_match"]:
        return {"matched": False, "similarity": matches[0]["similarity"] if matches else 0}

    best = matches[0]
    case = CASES[best["case_id"]]
    return {
        "matched": True,
        "similarity": best["similarity"],
        "case_number": case["case_number"],
        "child_name": case["child_name"],
        "guardian_phone": case["guardian_phone"],
        "guardian_name": case["guardian_name"],
        "last_seen_location": case["last_seen_location"],
    }

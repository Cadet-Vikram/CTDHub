"""
/api/cases — Register, retrieve, and update missing children cases.
"""
import io
import pickle
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from PIL import Image

from services.face_recognition import FaceRecognitionService
from services.age_progression import AgeProgressionService

router = APIRouter()

# In-memory store for prototype (replace with DB + S3 in production)
CASES: dict[int, dict] = {}
_counter = 0


def next_id():
    global _counter
    _counter += 1
    return _counter


class CaseOut(BaseModel):
    id: int
    case_number: str
    child_name: str
    age_at_missing: float
    gender: str
    date_missing: str
    last_seen_location: str
    guardian_name: str
    guardian_phone: str
    status: str
    has_embedding: bool
    photo_url: Optional[str] = None


@router.post("/", response_model=CaseOut)
async def create_case(
    child_name: str = Form(...),
    age_at_missing: float = Form(...),
    gender: str = Form(...),
    date_missing: str = Form(...),
    last_seen_location: str = Form(...),
    last_seen_lat: float = Form(0.0),
    last_seen_lng: float = Form(0.0),
    guardian_name: str = Form(...),
    guardian_phone: str = Form(...),
    guardian_email: str = Form(""),
    description: str = Form(""),
    distinguishing_marks: str = Form(""),
    aadhaar_number: str = Form(""),
    photo: Optional[UploadFile] = File(None),
):
    face_svc = FaceRecognitionService()
    case_id = next_id()
    case_number = f"CTD-{datetime.utcnow().year}-{case_id:05d}"

    embedding_bytes = None
    photo_url = None

    if photo:
        img_bytes = await photo.read()
        image = Image.open(io.BytesIO(img_bytes))

        # Extract face embedding
        embedding = face_svc.detect_and_embed(image)
        if embedding is not None:
            embedding_bytes = face_svc.serialize_embedding(embedding)

        # Generate age progressions for children < 15
        if age_at_missing < 15:
            age_svc = AgeProgressionService()
            progressions = age_svc.generate_all_progressions(image, age_at_missing)
            # In production, upload these to S3
            # For prototype, we just note they were generated
            _ = progressions

        photo_url = f"/photos/{case_number}_original.jpg"  # Simulated S3 URL

    case = {
        "id": case_id,
        "case_number": case_number,
        "child_name": child_name,
        "age_at_missing": age_at_missing,
        "gender": gender,
        "date_missing": date_missing,
        "last_seen_location": last_seen_location,
        "last_seen_lat": last_seen_lat,
        "last_seen_lng": last_seen_lng,
        "guardian_name": guardian_name,
        "guardian_phone": guardian_phone,
        "guardian_email": guardian_email,
        "description": description,
        "distinguishing_marks": distinguishing_marks,
        "aadhaar_number": aadhaar_number[:4] + "****" if aadhaar_number else "",
        "status": "open",
        "embedding_bytes": embedding_bytes,
        "photo_url": photo_url,
        "has_embedding": embedding_bytes is not None,
        "created_at": datetime.utcnow().isoformat(),
    }
    CASES[case_id] = case
    return CaseOut(**{k: v for k, v in case.items() if k != "embedding_bytes"})


@router.get("/", response_model=list[CaseOut])
def list_cases(status: Optional[str] = None):
    results = list(CASES.values())
    if status:
        results = [c for c in results if c["status"] == status]
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return [CaseOut(**{k: v for k, v in c.items() if k != "embedding_bytes"}) for c in results]


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: int):
    if case_id not in CASES:
        raise HTTPException(status_code=404, detail="Case not found")
    c = CASES[case_id]
    return CaseOut(**{k: v for k, v in c.items() if k != "embedding_bytes"})


@router.patch("/{case_id}/status")
def update_status(case_id: int, status: str):
    if case_id not in CASES:
        raise HTTPException(status_code=404, detail="Case not found")
    valid = {"open", "found", "closed", "investigating"}
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid}")
    CASES[case_id]["status"] = status
    return {"case_id": case_id, "status": status}

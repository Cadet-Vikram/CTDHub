"""
/api/sightings — Report and retrieve child sightings.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

router = APIRouter()
SIGHTINGS: dict[int, dict] = {}
_counter = 0


def next_id():
    global _counter
    _counter += 1
    return _counter


class SightingOut(BaseModel):
    id: int
    case_id: Optional[int]
    location_name: str
    latitude: float
    longitude: float
    similarity_score: Optional[float]
    notes: str
    verified: bool
    created_at: str


@router.post("/", response_model=SightingOut)
async def report_sighting(
    case_id: Optional[int] = Form(None),
    location_name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    notes: str = Form(""),
    reporter_phone: str = Form(""),
    photo: Optional[UploadFile] = File(None),
):
    sid = next_id()
    similarity_score = None

    if photo and case_id:
        import io
        from PIL import Image
        from services.face_recognition import FaceRecognitionService
        from routes.cases import CASES

        face_svc = FaceRecognitionService()
        img_bytes = await photo.read()
        image = Image.open(io.BytesIO(img_bytes))
        embedding = face_svc.detect_and_embed(image)

        case = CASES.get(case_id)
        if embedding is not None and case and case.get("embedding_bytes"):
            stored_emb = face_svc.deserialize_embedding(case["embedding_bytes"])
            similarity_score = round(face_svc.cosine_similarity(embedding, stored_emb), 4)

    sighting = {
        "id": sid,
        "case_id": case_id,
        "location_name": location_name,
        "latitude": latitude,
        "longitude": longitude,
        "similarity_score": similarity_score,
        "notes": notes,
        "reporter_phone": reporter_phone,
        "verified": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    SIGHTINGS[sid] = sighting
    return SightingOut(**sighting)


@router.get("/case/{case_id}", response_model=list[SightingOut])
def get_sightings_for_case(case_id: int):
    return [SightingOut(**s) for s in SIGHTINGS.values() if s.get("case_id") == case_id]


@router.patch("/{sighting_id}/verify")
def verify_sighting(sighting_id: int):
    if sighting_id not in SIGHTINGS:
        raise HTTPException(404, "Sighting not found")
    SIGHTINGS[sighting_id]["verified"] = True
    return {"verified": True}

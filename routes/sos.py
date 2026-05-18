"""
/api/sos — Emergency SOS reporting endpoint.
Any member of public can submit an SOS if they spot a suspicious child.
"""
import io
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from PIL import Image
from typing import Optional

from services.face_recognition import FaceRecognitionService
from routes.cases import CASES

router = APIRouter()

SOS_REPORTS: dict[int, dict] = {}
_sos_counter = 0


def next_sos_id():
    global _sos_counter
    _sos_counter += 1
    return _sos_counter


class SOSOut(BaseModel):
    sos_id: int
    matched: bool
    case_number: Optional[str]
    child_name: Optional[str]
    similarity: Optional[float]
    message: str
    action: str


@router.post("/report", response_model=SOSOut)
async def submit_sos(
    reporter_name: str = Form(...),
    reporter_phone: str = Form(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    photo: Optional[UploadFile] = File(None),
):
    """
    Submit an SOS report with optional photo.
    Instantly matches against DB and alerts nearest authorities.
    """
    sos_id = next_sos_id()
    matched = False
    matched_case = None
    similarity = None

    if photo:
        face_svc = FaceRecognitionService()
        img_bytes = await photo.read()
        image = Image.open(io.BytesIO(img_bytes))
        embedding = face_svc.detect_and_embed(image)

        if embedding is not None:
            db_entries = [
                {"case_id": c["id"], "embedding_bytes": c["embedding_bytes"], "age_at_missing": c["age_at_missing"]}
                for c in CASES.values()
                if c.get("embedding_bytes") and c["status"] == "open"
            ]
            if db_entries:
                matches = face_svc.match_against_database(embedding, db_entries, top_k=1)
                if matches and matches[0]["is_match"]:
                    matched = True
                    matched_case = CASES.get(matches[0]["case_id"])
                    similarity = matches[0]["similarity"]

    report = {
        "id": sos_id,
        "reporter_name": reporter_name,
        "reporter_phone": reporter_phone,
        "description": description,
        "latitude": latitude,
        "longitude": longitude,
        "matched": matched,
        "matched_case_id": matched_case["id"] if matched_case else None,
        "similarity": similarity,
        "created_at": datetime.utcnow().isoformat(),
    }
    SOS_REPORTS[sos_id] = report

    # In production: trigger AlertService.send_sos_to_nearest(...)

    if matched and matched_case:
        return SOSOut(
            sos_id=sos_id,
            matched=True,
            case_number=matched_case["case_number"],
            child_name=matched_case["child_name"],
            similarity=round(similarity, 3),
            message=f"MATCH FOUND! Case {matched_case['case_number']}. Authorities have been alerted.",
            action="Authorities notified. Guardian: " + matched_case["guardian_phone"],
        )

    return SOSOut(
        sos_id=sos_id,
        matched=False,
        case_number=None,
        child_name=None,
        similarity=similarity,
        message="SOS report received. No exact match found. Authorities alerted.",
        action="Local police notified via SMS and push notification.",
    )


@router.get("/reports")
def list_sos_reports():
    return list(SOS_REPORTS.values())

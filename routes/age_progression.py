"""Age Progression Routes"""
import cv2
import uuid
import os
import base64
import logging
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from utils.database import get_db, ChildRecord, AgeProgressionRecord
from utils.face_engine import load_image_from_bytes
from utils.age_progression import progress_age, generate_age_series

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/progress/{case_id}")
async def age_progress_case(
    case_id: str,
    target_age: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ChildRecord).where(ChildRecord.case_id == case_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(404, "Case not found")
    if not child.photo_path or not os.path.exists(child.photo_path):
        raise HTTPException(422, "No enrollment photo found for this case")

    image = cv2.imread(child.photo_path)
    current_age = child.age_at_disappearance or 0
    progressed, confidence = progress_age(image, current_age, target_age)

    os.makedirs("uploads/age_progression", exist_ok=True)
    out_path = f"uploads/age_progression/{case_id}_age{target_age}.jpg"
    cv2.imwrite(out_path, progressed)

    record = AgeProgressionRecord(
        case_id=case_id,
        original_photo=child.photo_path,
        progressed_photo=out_path,
        original_age=current_age,
        target_age=target_age,
        years_progressed=target_age - current_age,
    )
    db.add(record)
    await db.commit()

    _, buffer = cv2.imencode(".jpg", progressed)
    img_b64 = base64.b64encode(buffer).decode()

    return {
        "case_id": case_id,
        "original_age": current_age,
        "target_age": target_age,
        "confidence": confidence,
        "image_base64": img_b64,
        "saved_path": out_path,
    }


@router.post("/series/{case_id}")
async def age_series(case_id: str, max_age: int = Form(25), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChildRecord).where(ChildRecord.case_id == case_id))
    child = result.scalar_one_or_none()
    if not child or not child.photo_path:
        raise HTTPException(404, "Case or photo not found")

    image = cv2.imread(child.photo_path)
    series = generate_age_series(image, child.age_at_disappearance or 0, max_age=max_age)

    output = []
    for item in series:
        _, buf = cv2.imencode(".jpg", item["image"])
        output.append({
            "age": item["age"],
            "years_progressed": item["years_progressed"],
            "confidence": item["confidence"],
            "image_base64": base64.b64encode(buf).decode(),
        })
    return {"case_id": case_id, "series": output}

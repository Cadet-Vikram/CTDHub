"""
Children API - Register and manage missing children records
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import json, os, uuid, hashlib
from datetime import datetime

from app.database import get_db
from app.models.child import Child

router = APIRouter()
UPLOAD_DIR = "uploads/faces"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ChildCreate(BaseModel):
    name: str
    age: int
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    eye_color: Optional[str] = None
    hair_color: Optional[str] = None
    skin_tone: Optional[str] = None
    identifying_marks: Optional[str] = None
    last_seen_location: Optional[str] = None
    last_seen_lat: Optional[float] = None
    last_seen_lng: Optional[float] = None
    last_seen_date: Optional[str] = None
    guardian_name: str
    guardian_phone: str
    guardian_email: Optional[str] = None
    aadhaar_number: Optional[str] = None  # Will be hashed before storage
    police_station: Optional[str] = None
    fir_number: Optional[str] = None
    notes: Optional[str] = None


@router.post("/register")
async def register_missing_child(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(None),
    height_cm: float = Form(None),
    weight_kg: float = Form(None),
    eye_color: str = Form(None),
    hair_color: str = Form(None),
    skin_tone: str = Form(None),
    identifying_marks: str = Form(None),
    last_seen_location: str = Form(None),
    last_seen_lat: float = Form(None),
    last_seen_lng: float = Form(None),
    last_seen_date: str = Form(None),
    guardian_name: str = Form(...),
    guardian_phone: str = Form(...),
    guardian_email: str = Form(None),
    aadhaar_number: str = Form(None),
    police_station: str = Form(None),
    fir_number: str = Form(None),
    notes: str = Form(None),
    face_image: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    """Register a new missing child with optional face image"""

    child_id = str(uuid.uuid4())
    face_path = None
    embedding = None

    # Handle face image upload and embedding extraction
    if face_image and face_image.filename:
        image_bytes = await face_image.read()
        ext = face_image.filename.split(".")[-1]
        face_path = f"{UPLOAD_DIR}/{child_id}.{ext}"

        with open(face_path, "wb") as f:
            f.write(image_bytes)

        # Extract embedding (skip if child < 5 years)
        face_service = request.app.state.face_service
        embedding = face_service.extract_embedding(image_bytes, age=age)

    # Hash Aadhaar if provided (NEVER store raw)
    aadhaar_hash = None
    aadhaar_verified = False
    if aadhaar_number:
        aadhaar_hash = hashlib.sha256(aadhaar_number.encode()).hexdigest()
        aadhaar_verified = True  # In prod: verify via UIDAI API

    # Parse date
    last_seen = None
    if last_seen_date:
        try:
            last_seen = datetime.fromisoformat(last_seen_date)
        except Exception:
            pass

    child = Child(
        id=child_id,
        name=name,
        age=age,
        gender=gender,
        height_cm=height_cm,
        weight_kg=weight_kg,
        eye_color=eye_color,
        hair_color=hair_color,
        skin_tone=skin_tone,
        identifying_marks=identifying_marks,
        last_seen_location=last_seen_location,
        last_seen_lat=last_seen_lat,
        last_seen_lng=last_seen_lng,
        last_seen_date=last_seen,
        guardian_name=guardian_name,
        guardian_phone=guardian_phone,
        guardian_email=guardian_email,
        aadhaar_hash=aadhaar_hash,
        aadhaar_verified=aadhaar_verified,
        has_biometrics=embedding is not None,
        too_young_for_biometrics=age < 5,
        face_embedding=embedding,
        face_image_path=face_path,
        police_station=police_station,
        fir_number=fir_number,
        notes=notes,
    )

    db.add(child)
    await db.commit()
    await db.refresh(child)

    return {
        "success": True,
        "child_id": child_id,
        "message": f"Missing child '{name}' registered successfully",
        "biometrics_captured": embedding is not None,
        "too_young_for_biometrics": age < 5,
        "aadhaar_verified": aadhaar_verified,
        "child": child.to_dict(),
    }


@router.get("/list")
async def list_missing_children(
    status: str = "missing",
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all missing children"""
    query = select(Child).where(Child.status == status).offset(skip).limit(limit)
    result = await db.execute(query)
    children = result.scalars().all()
    return {
        "total": len(children),
        "children": [c.to_dict() for c in children],
    }


@router.get("/{child_id}")
async def get_child(child_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific child record"""
    result = await db.execute(select(Child).where(Child.id == child_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    return child.to_dict()


@router.patch("/{child_id}/status")
async def update_child_status(
    child_id: str,
    status: str,
    notes: str = None,
    db: AsyncSession = Depends(get_db),
):
    """Update child status (missing → found → closed)"""
    result = await db.execute(select(Child).where(Child.id == child_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    valid_statuses = ["missing", "found", "closed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")

    child.status = status
    if notes:
        child.notes = (child.notes or "") + f"\n[{datetime.now().isoformat()}] {notes}"

    await db.commit()
    return {"success": True, "child_id": child_id, "new_status": status}


@router.delete("/{child_id}")
async def delete_child_record(child_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a child record (admin only in production)"""
    result = await db.execute(select(Child).where(Child.id == child_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    await db.delete(child)
    await db.commit()
    return {"success": True, "message": "Record deleted"}

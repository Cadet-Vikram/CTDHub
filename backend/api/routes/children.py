"""Children Registry routes"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Child, get_db
from services.model_client import extract_embedding

router = APIRouter()
UPLOAD_DIR = "uploads/children"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/register")
async def register_child(
    name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    description: Optional[str] = Form(None),
    last_seen_location: Optional[str] = Form(None),
    last_seen_date: Optional[str] = Form(None),
    reported_by: Optional[str] = Form(None),
    contact_number: Optional[str] = Form(None),
    aadhaar_number: Optional[str] = Form(None),
    geolocation_lat: Optional[float] = Form(None),
    geolocation_lng: Optional[float] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    child_id = str(uuid.uuid4())
    photo_path = None
    embedding_json = None

    if photo:
        ext = (photo.filename or "jpg").rsplit(".", 1)[-1]
        filename = f"{child_id}.{ext}"
        photo_path = os.path.join(UPLOAD_DIR, filename).replace("\\", "/")
        content = await photo.read()

        with open(photo_path, "wb") as f:
            f.write(content)

        if age >= 5:
            try:
                model_result = await extract_embedding(content, photo.filename)
                embedding = model_result.get("embedding")
                if embedding is not None:
                    embedding_json = json.dumps(embedding)
            except Exception as exc:
                raise HTTPException(status_code=503, detail=f"Model service unavailable: {exc}") from exc

    child = Child(
        id=child_id,
        name=name,
        age=age,
        gender=gender,
        description=description,
        last_seen_location=last_seen_location,
        last_seen_date=datetime.fromisoformat(last_seen_date) if last_seen_date else None,
        reported_by=reported_by,
        contact_number=contact_number,
        aadhaar_number=aadhaar_number[-4:] if aadhaar_number else None,
        photo_path=photo_path,
        face_embedding=embedding_json,
        geolocation_lat=geolocation_lat,
        geolocation_lng=geolocation_lng,
        status="missing",
    )
    db.add(child)
    await db.commit()

    return JSONResponse(
        {
            "success": True,
            "child_id": child_id,
            "embedding_extracted": embedding_json is not None,
        }
    )


@router.get("/")
async def list_children(
    status: Optional[str] = "missing",
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    q = select(Child)
    if status and status != "all":
        q = q.where(Child.status == status)
    q = q.order_by(Child.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    rows = result.scalars().all()

    return [
        {
            "id": c.id,
            "name": c.name,
            "age": c.age,
            "gender": c.gender,
            "status": c.status,
            "last_seen_location": c.last_seen_location,
            "last_seen_date": c.last_seen_date.isoformat() if c.last_seen_date else None,
            "contact_number": c.contact_number,
            "photo_path": c.photo_path,
            "geolocation_lat": c.geolocation_lat,
            "geolocation_lng": c.geolocation_lng,
            "created_at": c.created_at.isoformat(),
            "has_embedding": c.face_embedding is not None,
        }
        for c in rows
    ]


@router.get("/{child_id}")
async def get_child(child_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Child).where(Child.id == child_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    return {
        "id": child.id,
        "name": child.name,
        "age": child.age,
        "gender": child.gender,
        "description": child.description,
        "status": child.status,
        "last_seen_location": child.last_seen_location,
        "contact_number": child.contact_number,
        "photo_path": child.photo_path,
        "geolocation_lat": child.geolocation_lat,
        "geolocation_lng": child.geolocation_lng,
        "created_at": child.created_at.isoformat(),
        "has_embedding": child.face_embedding is not None,
    }


@router.patch("/{child_id}/status")
async def update_status(child_id: str, status: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Child).where(Child.id == child_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    child.status = status
    await db.commit()
    return {"success": True, "new_status": status}

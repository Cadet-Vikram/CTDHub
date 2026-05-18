"""
Child Registry Routes - CRUD for missing child cases
"""

import uuid
import datetime
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from utils.database import get_db, ChildRecord
from utils.alert_system import broadcast_missing_child_alert

router = APIRouter()
logger = logging.getLogger(__name__)


class ChildCreate(BaseModel):
    name: str
    age_at_disappearance: int
    date_of_birth: Optional[str] = None
    gender: str
    missing_since: Optional[str] = None
    last_seen_location: str
    last_seen_lat: Optional[float] = None
    last_seen_lon: Optional[float] = None
    guardian_name: str
    guardian_phone: str
    guardian_email: Optional[str] = None
    description: Optional[str] = None
    distinctive_features: Optional[str] = None
    police_case_number: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    aadhaar_number: Optional[str] = None
    is_under_5: bool = False


class ChildUpdate(BaseModel):
    status: Optional[str] = None
    last_seen_location: Optional[str] = None
    description: Optional[str] = None


def generate_case_id() -> str:
    now = datetime.datetime.utcnow()
    return f"CTD{now.year}{now.month:02d}{now.day:02d}{uuid.uuid4().hex[:6].upper()}"


@router.post("/register")
async def register_child(child: ChildCreate, db: AsyncSession = Depends(get_db)):
    """Register a new missing child case."""
    case_id = generate_case_id()
    missing_dt = None
    if child.missing_since:
        try:
            missing_dt = datetime.datetime.fromisoformat(child.missing_since)
        except ValueError:
            missing_dt = datetime.datetime.utcnow()
    else:
        missing_dt = datetime.datetime.utcnow()

    # Hash Aadhaar if provided
    aadhaar_hash = None
    if child.aadhaar_number:
        import hashlib
        aadhaar_hash = hashlib.sha256(child.aadhaar_number.encode()).hexdigest()

    record = ChildRecord(
        case_id=case_id,
        name=child.name,
        age_at_disappearance=child.age_at_disappearance,
        date_of_birth=child.date_of_birth,
        gender=child.gender,
        missing_since=missing_dt,
        last_seen_location=child.last_seen_location,
        last_seen_lat=child.last_seen_lat,
        last_seen_lon=child.last_seen_lon,
        guardian_name=child.guardian_name,
        guardian_phone=child.guardian_phone,
        guardian_email=child.guardian_email,
        description=child.description,
        distinctive_features=child.distinctive_features,
        police_case_number=child.police_case_number,
        district=child.district,
        state=child.state,
        aadhaar_number=aadhaar_hash,
        is_under_5=child.is_under_5,
        status="missing",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Fire alerts
    broadcast_missing_child_alert({
        "name": child.name,
        "age_at_disappearance": child.age_at_disappearance,
        "last_seen_location": child.last_seen_location,
        "case_id": case_id,
        "guardian_phone": child.guardian_phone,
        "guardian_email": child.guardian_email,
        "missing_since": str(missing_dt),
        "description": child.description,
    })

    return {"case_id": case_id, "status": "registered", "message": "Alerts sent to authorities"}


@router.get("/case/{case_id}")
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChildRecord).where(ChildRecord.case_id == case_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(404, "Case not found")
    return _child_to_dict(child)


@router.get("/search")
async def search_cases(
    q: Optional[str] = Query(None, description="Search by name, location, or case ID"),
    state: Optional[str] = Query(None),
    status: Optional[str] = Query("missing"),
    is_under_5: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ChildRecord)
    if status:
        stmt = stmt.where(ChildRecord.status == status)
    if state:
        stmt = stmt.where(ChildRecord.state == state)
    if is_under_5 is not None:
        stmt = stmt.where(ChildRecord.is_under_5 == is_under_5)
    if q:
        stmt = stmt.where(or_(
            ChildRecord.name.ilike(f"%{q}%"),
            ChildRecord.case_id.ilike(f"%{q}%"),
            ChildRecord.last_seen_location.ilike(f"%{q}%"),
            ChildRecord.district.ilike(f"%{q}%"),
        ))
    stmt = stmt.order_by(ChildRecord.missing_since.desc()).limit(50)
    result = await db.execute(stmt)
    children = result.scalars().all()
    return {"total": len(children), "cases": [_child_to_dict(c) for c in children]}


@router.get("/list")
async def list_all(
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChildRecord)
        .order_by(ChildRecord.missing_since.desc())
        .offset(offset).limit(limit)
    )
    children = result.scalars().all()
    total = await db.execute(select(ChildRecord))
    return {
        "total": len(total.scalars().all()),
        "cases": [_child_to_dict(c) for c in children],
    }


@router.patch("/case/{case_id}")
async def update_case(case_id: str, update: ChildUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChildRecord).where(ChildRecord.case_id == case_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(404, "Case not found")
    if update.status:
        child.status = update.status
    if update.last_seen_location:
        child.last_seen_location = update.last_seen_location
    if update.description:
        child.description = update.description
    await db.commit()
    return {"status": "updated", "case_id": case_id}


def _child_to_dict(c: ChildRecord) -> dict:
    return {
        "case_id": c.case_id,
        "name": c.name,
        "age_at_disappearance": c.age_at_disappearance,
        "date_of_birth": c.date_of_birth,
        "gender": c.gender,
        "missing_since": str(c.missing_since),
        "last_seen_location": c.last_seen_location,
        "last_seen_lat": c.last_seen_lat,
        "last_seen_lon": c.last_seen_lon,
        "guardian_name": c.guardian_name,
        "guardian_phone": c.guardian_phone,
        "status": c.status,
        "description": c.description,
        "distinctive_features": c.distinctive_features,
        "police_case_number": c.police_case_number,
        "district": c.district,
        "state": c.state,
        "is_under_5": c.is_under_5,
        "photo": c.photo_path,
        "has_face_enrollment": c.face_embedding is not None,
        "created_at": str(c.created_at),
    }

"""Emergency Alerts routes"""

import json
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Alert, Child, get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Background task stubs (wire up Twilio / Firebase here) ─────────────────────

async def _send_sms(phone: str, message: str):
    logger.info(f"[SMS → {phone}] {message[:80]}")
    await asyncio.sleep(0)   # replace with real API call


async def _notify_authorities(child_id: str, lat: Optional[float], lng: Optional[float]):
    logger.info(f"[AUTHORITY] child={child_id} lat={lat} lng={lng}")
    await asyncio.sleep(0)


# ── Request schemas ────────────────────────────────────────────────────────────

class SOSRequest(BaseModel):
    child_id:       str
    reporter_name:  str
    reporter_phone: str
    location_lat:   Optional[float] = None
    location_lng:   Optional[float] = None
    message:        Optional[str]   = None


class BroadcastRequest(BaseModel):
    child_id:  str
    radius_km: float = 10.0
    message:   Optional[str] = None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/sos")
async def trigger_sos(
    req: SOSRequest,
    bg:  BackgroundTasks,
    db:  AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Child).where(Child.id == req.child_id))
    child  = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    msg = (
        f"SOS ALERT: {child.name} (Age {child.age}) may have been spotted. "
        f"Reporter: {req.reporter_name} ({req.reporter_phone}). "
        f"Location: {req.location_lat}, {req.location_lng}. "
        f"{req.message or ''}"
    )

    alert = Alert(
        child_id     = req.child_id,
        alert_type   = "sos",
        message      = msg,
        location_lat = req.location_lat,
        location_lng = req.location_lng,
        sent_to      = json.dumps([child.contact_number]),
        status       = "sent",
    )
    db.add(alert)
    await db.commit()

    if child.contact_number:
        bg.add_task(_send_sms, child.contact_number, msg)
    bg.add_task(_notify_authorities, req.child_id, req.location_lat, req.location_lng)

    return {"success": True, "alert_id": alert.id, "message": "SOS alert triggered"}


@router.post("/broadcast")
async def broadcast_alert(
    req: BroadcastRequest,
    bg:  BackgroundTasks,
    db:  AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Child).where(Child.id == req.child_id))
    child  = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    msg = (
        f"MISSING CHILD ALERT: {child.name}, {child.age} yrs, {child.gender}. "
        f"Last seen: {child.last_seen_location}. "
        f"Contact: {child.contact_number}. "
        f"{req.message or 'Please help us find this child.'}"
    )

    alert = Alert(
        child_id   = req.child_id,
        alert_type = "broadcast",
        message    = msg,
        status     = "broadcast",
    )
    db.add(alert)
    await db.commit()

    return {
        "success":   True,
        "alert_id":  alert.id,
        "radius_km": req.radius_km,
        "message":   f"Broadcast sent within {req.radius_km} km radius",
    }


@router.get("/")
async def list_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Alert).order_by(Alert.created_at.desc()).limit(50)
    )
    rows = result.scalars().all()
    return [
        {
            "id":         a.id,
            "child_id":   a.child_id,
            "alert_type": a.alert_type,
            "message":    a.message,
            "status":     a.status,
            "created_at": a.created_at.isoformat(),
        }
        for a in rows
    ]

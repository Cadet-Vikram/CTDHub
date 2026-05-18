"""
/api/alerts — Create and retrieve AMBER-style alerts.
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
ALERTS: dict[int, dict] = {}
_counter = 0

def next_id():
    global _counter
    _counter += 1
    return _counter

class AlertCreate(BaseModel):
    case_id: int
    alert_type: str = "AMBER"
    message: str
    center_lat: float
    center_lng: float
    radius_km: float = 50.0

class AlertOut(BaseModel):
    id: int
    case_id: int
    alert_type: str
    message: str
    radius_km: float
    status: str
    created_at: str

@router.post("/", response_model=AlertOut)
def create_alert(body: AlertCreate):
    aid = next_id()
    alert = {
        "id": aid, "case_id": body.case_id, "alert_type": body.alert_type,
        "message": body.message, "center_lat": body.center_lat,
        "center_lng": body.center_lng, "radius_km": body.radius_km,
        "status": "active", "created_at": datetime.utcnow().isoformat(),
    }
    ALERTS[aid] = alert
    return AlertOut(**alert)

@router.get("/active", response_model=list[AlertOut])
def active_alerts():
    return [AlertOut(**a) for a in ALERTS.values() if a["status"] == "active"]

@router.patch("/{alert_id}/resolve")
def resolve_alert(alert_id: int):
    if alert_id not in ALERTS:
        raise HTTPException(404, "Alert not found")
    ALERTS[alert_id]["status"] = "resolved"
    return {"resolved": True}

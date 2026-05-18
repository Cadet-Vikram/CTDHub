"""SOS Emergency API - Trigger instant AMBER-alert style notifications"""

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import logging, json

from app.database import get_db
from app.models.alert import Alert

logger = logging.getLogger(__name__)
router = APIRouter()


class SOSRequest(BaseModel):
    child_id: str
    child_name: str
    reporter_phone: str
    location_description: str
    lat: float
    lng: float
    additional_info: Optional[str] = ""


@router.post("/trigger")
async def trigger_sos(
    sos: SOSRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """🚨 Trigger SOS emergency alert - sends to all nearby authorities"""
    alert_service = request.app.state.alert_service

    result = await alert_service.send_sos_alert(
        child_id=sos.child_id,
        child_name=sos.child_name,
        location=sos.location_description,
        lat=sos.lat,
        lng=sos.lng,
        reporter_phone=sos.reporter_phone,
        additional_info=sos.additional_info,
    )

    # Save alert to DB
    alert = Alert(
        child_id=sos.child_id,
        child_name=sos.child_name,
        alert_type="sos",
        severity="critical",
        message=result["message"],
        location=sos.location_description,
        lat=sos.lat,
        lng=sos.lng,
    )
    db.add(alert)
    await db.commit()

    # Broadcast to dashboard
    await alert_service.broadcast_to_dashboard({
        "type": "SOS_ALERT",
        "child_id": sos.child_id,
        "child_name": sos.child_name,
        "location": sos.location_description,
        "lat": sos.lat,
        "lng": sos.lng,
        "severity": "critical",
    })

    return result


@router.websocket("/ws")
async def alert_websocket(websocket: WebSocket, request: Request):
    """WebSocket endpoint for real-time dashboard alerts"""
    await websocket.accept()
    alert_service = request.app.state.alert_service
    await alert_service.register_websocket(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for keepalive
            await websocket.send_text(json.dumps({"type": "ping", "data": data}))
    except WebSocketDisconnect:
        await alert_service.unregister_websocket(websocket)

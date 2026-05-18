"""WebSocket — real-time alert broadcast"""

import json
import logging
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
ws_router = APIRouter()
_clients: List[WebSocket] = []


@ws_router.websocket("/alerts")
async def ws_alerts(ws: WebSocket):
    await ws.accept()
    _clients.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            await _broadcast({"type": "message", "data": data})
    except WebSocketDisconnect:
        _clients.remove(ws)


async def _broadcast(msg: dict):
    dead = []
    for c in _clients:
        try:
            await c.send_text(json.dumps(msg))
        except Exception:
            dead.append(c)
    for d in dead:
        _clients.remove(d)

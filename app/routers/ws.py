from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json

router = APIRouter()

# Salas de comunicacion: rooms[link_id] = [websocket1, websocket2]
rooms: Dict[str, List[WebSocket]] = {}


@router.websocket("/link/{link_id}")
async def link_websocket(websocket: WebSocket, link_id: str):
    """WebSocket para comunicacion en tiempo real entre los dos tecnicos del enlace."""
    await websocket.accept()
    rooms.setdefault(link_id, []).append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            dead = []
            for ws in rooms.get(link_id, []):
                if ws is not websocket:
                    try:
                        await ws.send_text(json.dumps(message))
                    except Exception:
                        dead.append(ws)
            for ws in dead:
                rooms[link_id].remove(ws)

    except WebSocketDisconnect:
        room = rooms.get(link_id, [])
        if websocket in room:
            room.remove(websocket)
        if not room:
            rooms.pop(link_id, None)

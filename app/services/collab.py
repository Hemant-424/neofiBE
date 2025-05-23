from fastapi import WebSocket
from typing import Dict, List

class CollaborationManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, event_id: str, websocket: WebSocket):
        await websocket.accept()
        if event_id not in self.active_connections:
            self.active_connections[event_id] = []
        self.active_connections[event_id].append(websocket)

    def disconnect(self, event_id: str, websocket: WebSocket):
        self.active_connections[event_id].remove(websocket)
        if not self.active_connections[event_id]:
            del self.active_connections[event_id]

    async def broadcast(self, event_id: str, message: dict):
        for connection in self.active_connections.get(event_id, []):
            await connection.send_json(message)

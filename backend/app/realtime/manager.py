import asyncio
from typing import Any
from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    """In-memory registry of WebSocket connections for one backend instance."""

    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, conversation_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.setdefault(conversation_id, set()).add(websocket)

    async def disconnect(self, conversation_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(conversation_id)
            if connections is None:
                return
            connections.discard(websocket)
            if not connections:
                del self._connections[conversation_id]

    async def broadcast(self, conversation_id: UUID, event: dict[str, Any]) -> None:
        async with self._lock:
            connections = list(self._connections.get(conversation_id, ()))

        for websocket in connections:
            try:
                await websocket.send_json(event)
            except Exception:
                await self.disconnect(conversation_id, websocket)


connection_manager = ConnectionManager()

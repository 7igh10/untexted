import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.schemas import UserPublic
from app.accounts.sessions import (
    SESSION_COOKIE_NAME,
    _csrf_strict,
    allowed_origins,
    get_session,
)
from app.conversations.service import ConversationNotFoundError, get_conversation
from app.models.user import User
from app.realtime.manager import connection_manager

router = APIRouter(tags=["realtime"])

UNAUTHORIZED_CLOSE_CODE = 4401
FORBIDDEN_CLOSE_CODE = 4403
NOT_FOUND_CLOSE_CODE = 4404


async def _close(websocket: WebSocket, code: int, reason: str | None = None) -> None:
    try:
        await websocket.close(code=code, reason=reason)
    except RuntimeError:
        pass


async def conversation_websocket(
    websocket: WebSocket,
    conversation_id: str,
) -> None:
    """Deliver new messages for one conversation over WebSocket."""
    origin = websocket.headers.get("origin")
    if origin is not None:
        if origin not in allowed_origins(websocket):
            await _close(websocket, FORBIDDEN_CLOSE_CODE, "Origin not allowed")
            return
    elif _csrf_strict():
        await _close(websocket, FORBIDDEN_CLOSE_CODE, "Origin required")
        return

    session_factory = getattr(websocket.app.state, "db_session_factory", None)
    if session_factory is None:
        await _close(websocket, 1013, "Database unavailable")
        return

    async with session_factory() as session:
        token = websocket.cookies.get(SESSION_COOKIE_NAME)
        user_session, _ = await get_session(session, token)
        if user_session is None:
            await _close(websocket, UNAUTHORIZED_CLOSE_CODE, "Not authenticated")
            return

        result = await session.execute(
            select(User).where(User.id == user_session.user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            await _close(websocket, UNAUTHORIZED_CLOSE_CODE, "Not authenticated")
            return

        try:
            conversation_uuid = UUID(conversation_id)
            conversation = await get_conversation(session, conversation_uuid, user)
        except (ValueError, TypeError, ConversationNotFoundError):
            await _close(websocket, NOT_FOUND_CLOSE_CODE, "Conversation not found")
            return

        await websocket.accept()
        await connection_manager.connect(conversation.id, websocket)
        try:
            await websocket.send_json(
                {"type": "connected", "conversation_id": str(conversation.id)}
            )
            while True:
                raw_message = await websocket.receive_text()
                try:
                    data = json.loads(raw_message)
                except json.JSONDecodeError:
                    await websocket.close(code=1003, reason="Invalid JSON")
                    break
                if not isinstance(data, dict):
                    await websocket.close(code=1003, reason="Invalid message")
                    break
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                else:
                    await websocket.close(code=1003, reason="Unsupported message")
                    break
        except WebSocketDisconnect:
            pass
        except Exception:
            try:
                await websocket.close(code=1011, reason="Internal error")
            except RuntimeError:
                pass
        finally:
            await connection_manager.disconnect(conversation.id, websocket)


@router.websocket("/conversations/{conversation_id}/ws")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str) -> None:
    await conversation_websocket(websocket, conversation_id)

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.sessions import validate_csrf
from app.conversations.service import ConversationNotFoundError
from app.database import get_db_session
from app.messages.schemas import MessageCreate, MessagePage, MessagePublic
from app.messages.service import (
    InvalidCursorError,
    MessageNotFoundError,
    NotFriendsError,
    list_messages,
    send_message,
)
from app.models.user import User

router = APIRouter(
    prefix="/conversations/{conversation_id}/messages",
    tags=["messages"],
    dependencies=[Depends(validate_csrf)],
)


@router.post("", response_model=MessagePublic, status_code=status.HTTP_201_CREATED)
async def create_message(
    conversation_id: str,
    payload: MessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessagePublic:
    """Send a message to a private conversation."""
    try:
        message = await send_message(
            session,
            conversation_id,
            current_user,
            payload.payload,
            reply_to_message_id=payload.reply_to_message_id,
        )
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        ) from None
    except NotFriendsError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users must be friends to send messages",
        ) from None
    except MessageNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        ) from None

    return MessagePublic.model_validate(message)


@router.get("", response_model=MessagePage)
async def read_messages(
    conversation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> MessagePage:
    """Return a page of conversation messages."""
    try:
        messages, next_cursor = await list_messages(
            session,
            conversation_id,
            current_user,
            limit=limit,
            cursor=cursor,
        )
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        ) from None
    except InvalidCursorError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor"
        ) from None

    return MessagePage(
        items=[MessagePublic.model_validate(message) for message in messages],
        next_cursor=next_cursor,
    )

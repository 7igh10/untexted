from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.schemas import UserPublic
from app.accounts.sessions import validate_csrf
from app.conversations.schemas import ConversationCreate, ConversationPublic
from app.conversations.service import (
    ConversationConflictError,
    ConversationNotFoundError,
    NotFriendsError,
    SelfConversationError,
    UserNotFoundError,
    get_conversation,
    get_or_create_conversation,
    list_conversations,
)
from app.database import get_db_session
from app.models.user import User

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(validate_csrf)],
)


@router.post("", response_model=ConversationPublic, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConversationPublic:
    """Create a private conversation or return the existing one."""
    try:
        conversation, created = await get_or_create_conversation(
            session,
            current_user,
            username=payload.username,
            user_id=payload.user_id,
            recipient_id=payload.recipient_id,
        )
    except SelfConversationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create a conversation with yourself",
        ) from None
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        ) from None
    except NotFriendsError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users must be friends to create a conversation",
        ) from None
    except ConversationConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation could not be processed",
        ) from None

    if not created:
        response.status_code = status.HTTP_200_OK

    other_user = (
        conversation.user_two
        if conversation.user_one_id == current_user.id
        else conversation.user_one
    )
    return ConversationPublic(
        id=conversation.id,
        created_at=conversation.created_at,
        other_user=UserPublic.model_validate(other_user),
    )


@router.get("", response_model=list[ConversationPublic])
async def read_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ConversationPublic]:
    """Return the current user's private conversations."""
    conversations = await list_conversations(session, current_user)
    result = []
    for conversation in conversations:
        other_user = (
            conversation.user_two
            if conversation.user_one_id == current_user.id
            else conversation.user_one
        )
        result.append(
            ConversationPublic(
                id=conversation.id,
                created_at=conversation.created_at,
                other_user=UserPublic.model_validate(other_user),
            )
        )
    return result


@router.get("/{conversation_id}", response_model=ConversationPublic)
async def read_conversation(
    conversation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConversationPublic:
    """Return one private conversation if the current user participates in it."""
    try:
        conversation = await get_conversation(session, conversation_id, current_user)
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        ) from None

    other_user = (
        conversation.user_two
        if conversation.user_one_id == current_user.id
        else conversation.user_one
    )
    return ConversationPublic(
        id=conversation.id,
        created_at=conversation.created_at,
        other_user=UserPublic.model_validate(other_user),
    )

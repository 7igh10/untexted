from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.dependencies import get_current_user
from app.accounts.schemas import UserPublic
from app.accounts.sessions import validate_csrf
from app.database import get_db_session
from app.friends.schemas import FriendRequestCreate, FriendRequestPublic
from app.friends.service import (
    AlreadyFriendsError,
    FriendRequestConflictError,
    FriendRequestForbiddenError,
    FriendRequestNotFoundError,
    PendingRequestExistsError,
    SelfFriendRequestError,
    UserNotFoundError,
    accept_friend_request,
    list_friends,
    list_incoming_requests,
    list_outgoing_requests,
    reject_friend_request,
    send_friend_request,
)
from app.models.user import User

router = APIRouter(
    prefix="/friends",
    tags=["friends"],
    dependencies=[Depends(validate_csrf)],
)


@router.post("/requests", response_model=FriendRequestPublic, status_code=status.HTTP_201_CREATED)
async def create_friend_request(
    payload: FriendRequestCreate,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FriendRequestPublic:
    """Send a friend request or auto-accept a mutual request."""
    try:
        friend_request, result = await send_friend_request(
            session,
            current_user,
            username=payload.username,
            user_id=payload.user_id,
            recipient_id=payload.recipient_id,
        )
    except SelfFriendRequestError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot send a friend request to yourself") from None
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from None
    except AlreadyFriendsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Users are already friends") from None
    except PendingRequestExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Friend request already pending") from None
    except FriendRequestConflictError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Friend request could not be processed") from None

    if result == "accepted":
        response.status_code = status.HTTP_200_OK
    try:
        response_model = FriendRequestPublic.model_validate(friend_request)
        return response_model
    except Exception as exc:
        raise


@router.get("/requests/incoming", response_model=list[FriendRequestPublic])
async def read_incoming_friend_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[FriendRequestPublic]:
    """Return pending friend requests received by the current user."""
    requests = await list_incoming_requests(session, current_user)
    return [FriendRequestPublic.model_validate(item) for item in requests]


@router.get("/requests/outgoing", response_model=list[FriendRequestPublic])
async def read_outgoing_friend_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[FriendRequestPublic]:
    """Return pending friend requests sent by the current user."""
    requests = await list_outgoing_requests(session, current_user)
    return [FriendRequestPublic.model_validate(item) for item in requests]


@router.post("/requests/{request_id}/accept", response_model=FriendRequestPublic)
async def accept_friend_request_endpoint(
    request_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FriendRequestPublic:
    """Accept a pending friend request."""
    try:
        friend_request = await accept_friend_request(session, request_id, current_user)
    except FriendRequestNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found") from None
    except FriendRequestForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot accept this friend request") from None
    except FriendRequestConflictError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Friend request is not pending") from None

    try:
        response_model = FriendRequestPublic.model_validate(friend_request)
        return response_model
    except Exception as exc:
        raise


@router.post("/requests/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_friend_request_endpoint(
    request_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """Reject a pending friend request."""
    try:
        await reject_friend_request(session, request_id, current_user)
    except FriendRequestNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found") from None
    except FriendRequestForbiddenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot reject this friend request") from None
    except FriendRequestConflictError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Friend request is not pending") from None


@router.get("", response_model=list[UserPublic])
async def read_friends(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[UserPublic]:
    """Return the current user's friends."""
    friends = await list_friends(session, current_user)
    return [UserPublic.model_validate(user) for user in friends]
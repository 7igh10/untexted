from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, USERNAME_MAX_LENGTH

USER_SEARCH_LIMIT = 20


async def search_users(
    session: AsyncSession,
    current_user: User,
    query: str,
) -> list[User]:
    """Return users whose username contains the normalized query."""
    statement = (
        select(User)
        .where(User.id != current_user.id)
        .where(User.username.contains(query, autoescape=True))
        .order_by(User.username.asc())
        .limit(USER_SEARCH_LIMIT)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())
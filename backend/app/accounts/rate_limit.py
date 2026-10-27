import asyncio
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import ceil


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


class LoginRateLimiter:
    def __init__(
        self,
        account_limit: int | None = None,
        account_window_minutes: int | None = None,
        ip_limit: int | None = None,
        ip_window_minutes: int | None = None,
    ) -> None:
        self.account_limit = account_limit or int(
            os.getenv("LOGIN_RATE_LIMIT_ACCOUNT", "5")
        )
        self.account_window = timedelta(
            minutes=account_window_minutes
            or int(os.getenv("LOGIN_RATE_LIMIT_ACCOUNT_WINDOW_MINUTES", "15"))
        )
        self.ip_limit = ip_limit or int(os.getenv("LOGIN_RATE_LIMIT_IP", "50"))
        self.ip_window = timedelta(
            minutes=ip_window_minutes
            or int(os.getenv("LOGIN_RATE_LIMIT_IP_WINDOW_MINUTES", "15"))
        )
        self._account_attempts: dict[tuple[str, str], list[datetime]] = defaultdict(list)
        self._ip_attempts: dict[str, list[datetime]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, username: str, ip: str) -> tuple[bool, int]:
        now = datetime.now(timezone.utc)
        account_key = (username.casefold(), ip)
        async with self._lock:
            self._prune(now)
            account_failures = self._account_attempts.get(account_key, [])
            ip_failures = self._ip_attempts.get(ip, [])

            if len(account_failures) >= self.account_limit:
                retry_after = self._retry_after(
                    account_failures[0], self.account_window, now
                )
                return False, retry_after
            if len(ip_failures) >= self.ip_limit:
                retry_after = self._retry_after(ip_failures[0], self.ip_window, now)
                return False, retry_after
            return True, 0

    async def record_failure(self, username: str, ip: str) -> None:
        now = datetime.now(timezone.utc)
        account_key = (username.casefold(), ip)
        async with self._lock:
            self._account_attempts[account_key].append(now)
            self._ip_attempts[ip].append(now)
            self._prune(now)

    async def record_success(self, username: str, ip: str) -> None:
        account_key = (username.casefold(), ip)
        async with self._lock:
            self._account_attempts.pop(account_key, None)

    def reset(self) -> None:
        self._account_attempts.clear()
        self._ip_attempts.clear()

    def _prune(self, now: datetime) -> None:
        for key, attempts in list(self._account_attempts.items()):
            recent = [item for item in attempts if now - item < self.account_window]
            if recent:
                self._account_attempts[key] = recent
            else:
                del self._account_attempts[key]

        for key, attempts in list(self._ip_attempts.items()):
            recent = [item for item in attempts if now - item < self.ip_window]
            if recent:
                self._ip_attempts[key] = recent
            else:
                del self._ip_attempts[key]

    @staticmethod
    def _retry_after(first_attempt: datetime, window: timedelta, now: datetime) -> int:
        remaining = (first_attempt + window - now).total_seconds()
        return max(1, ceil(remaining))


login_rate_limiter = LoginRateLimiter()
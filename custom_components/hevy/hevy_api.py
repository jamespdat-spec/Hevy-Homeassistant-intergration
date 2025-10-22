from __future__ import annotations

import aiohttp
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://api.hevyapp.com"

@dataclass
class HevyAuth:
    api_key: str
    email_or_username: str
    password: str
    auth_token: Optional[str] = None

class HevyClient:
    def __init__(self, session: aiohttp.ClientSession, auth: HevyAuth) -> None:
        self._session = session
        self._auth = auth

    @property
    def headers(self) -> Dict[str, str]:
        hdrs = {
            "x-api-key": self._auth.api_key,
            "Content-Type": "application/json",
            "accept-encoding": "gzip",
        }
        if self._auth.auth_token:
            hdrs["auth-token"] = self._auth.auth_token
        return hdrs

    async def login(self) -> None:
        """Login to Hevy and store auth-token."""
        url = f"{BASE_URL}/login"
        payload = {
            "emailOrUsername": self._auth.email_or_username,
            "password": self._auth.password,
        }
        _LOGGER.debug("Hevy: POST %s", url)
        async with self._session.post(url, json=payload, headers=self.headers, timeout=30) as resp:
            text = await resp.text()
            _LOGGER.debug("Hevy login status=%s body=%s", resp.status, text[:500])
            resp.raise_for_status()
            data = await resp.json()
        token = data.get("auth_token")
        if not token:
            raise RuntimeError("Hevy login succeeded but no auth_token returned")
        self._auth.auth_token = token

    async def _ensure_login(self) -> None:
        if not self._auth.auth_token:
            await self.login()

    async def get_account(self) -> Dict[str, Any]:
        await self._ensure_login()
        url = f"{BASE_URL}/account"
        _LOGGER.debug("Hevy: GET %s", url)
        async with self._session.get(url, headers=self.headers, timeout=30) as resp:
            if resp.status == 401:
                _LOGGER.info("Hevy token expired, re-logging in")
                self._auth.auth_token = None
                await self.login()
                return await self.get_account()
            resp.raise_for_status()
            return await resp.json()

    async def get_workout_count(self) -> int | None:
        await self._ensure_login()
        url = f"{BASE_URL}/workout_count"
        _LOGGER.debug("Hevy: GET %s", url)
        async with self._session.get(url, headers=self.headers, timeout=30) as resp:
            if resp.status == 401:
                self._auth.auth_token = None
                await self.login()
                return await self.get_workout_count()
            if resp.status == 404:
                return None
            resp.raise_for_status()
            data = await resp.json()
            # common shape: {"count": 1234}
            return data.get("count")

    async def list_workouts_paged(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Hit a paged workouts endpoint. Hevy endpoints vary; one observed path is /feed/workouts_paged.
        Fallback to /workouts if available.
        """
        await self._ensure_login()

        # Try /feed/workouts_paged first
        url = f"{BASE_URL}/feed/workouts_paged"
        params = {"page": page, "page_size": page_size}
        _LOGGER.debug("Hevy: GET %s params=%s", url, params)
        async with self._session.get(url, headers=self.headers, params=params, timeout=30) as resp:
            if resp.status in (401, 403):
                self._auth.auth_token = None
                await self.login()
                return await self.list_workouts_paged(page, page_size)
            if resp.status in (404, 405):
                # Fallback to /workouts
                alt = f"{BASE_URL}/workouts"
                _LOGGER.debug("Hevy: falling back to %s", alt)
                async with self._session.get(alt, headers=self.headers, params=params, timeout=30) as r2:
                    r2.raise_for_status()
                    return await r2.json()
            resp.raise_for_status()
            return await resp.json()

    async def latest_workout_summary(self) -> Dict[str, Any] | None:
        """Return best-effort summary of the latest workout."""
        page = await self.list_workouts_paged(page=1, page_size=1)
        items = page.get("items") or page.get("workouts") or []
        if not items:
            return None
        w = items[0]
        # heuristic field names
        started_at = w.get("started_at") or w.get("start_time") or w.get("created_at")
        duration_min = w.get("duration_minutes") or w.get("duration")  # could be seconds
        total_volume = w.get("total_volume") or w.get("volume")

        # Normalize duration if seconds
        if isinstance(duration_min, (int, float)) and duration_min and duration_min > 300:
            # assume seconds if very large
            duration_min = round(duration_min / 60, 1)

        return {
            "id": w.get("id"),
            "name": w.get("name") or w.get("title") or "Workout",
            "started_at": started_at,
            "duration_min": duration_min,
            "total_volume": total_volume,
        }

    async def weekly_volume(self) -> float | None:
        """Compute last 7 days volume across workouts (best effort)."""
        await self._ensure_login()
        volume = 0.0
        page = 1
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=7)
        while True:
            data = await self.list_workouts_paged(page=page, page_size=25)
            items = data.get("items") or data.get("workouts") or []
            if not items:
                break
            any_in_range = False
            for w in items:
                ts = w.get("started_at") or w.get("start_time") or w.get("created_at")
                if not ts:
                    continue
                try:
                    dt = datetime.fromisoformat(ts.replace("Z","+00:00"))
                except Exception:
                    continue
                if dt >= cutoff:
                    any_in_range = True
                    vol = w.get("total_volume") or w.get("volume") or 0
                    try:
                        volume += float(vol or 0)
                    except Exception:
                        pass
            if not any_in_range:
                break
            page += 1
        return round(volume, 2)

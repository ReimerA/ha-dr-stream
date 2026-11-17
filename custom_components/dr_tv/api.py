"""Small async client for DR's (unofficial) DRTV API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any

import aiohttp

from .const import API_BASE, API_PARAMS

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)
_IMAGE_SIZE_RE = re.compile(r"Width=\d+&Height=\d+")


class DRTVError(Exception):
    """Raised when DR's API cannot be reached or returns unexpected data."""


@dataclass(frozen=True, slots=True)
class Channel:
    """A DR live channel."""

    id: str
    title: str
    stream_url: str
    stream_url_subtitles: str | None = None
    logo: str | None = None


@dataclass(frozen=True, slots=True)
class Programme:
    """One programme in a channel's schedule."""

    channel_id: str
    title: str
    start: datetime
    end: datetime
    description: str | None = None
    image: str | None = None


def resize_image(url: str | None, width: int, height: int) -> str | None:
    """DR image URLs default to 3000px; ask DR's resizer for a smaller one."""
    if url is None:
        return None
    return _IMAGE_SIZE_RE.sub(f"Width={width}&Height={height}", url)


class DRTVClient:
    """Fetch channels and schedules from DR."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        try:
            async with self._session.get(
                f"{API_BASE}{path}",
                params={**API_PARAMS, **(params or {})},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except (TimeoutError, aiohttp.ClientError, ValueError) as err:
            raise DRTVError(f"Request to {path} failed: {err}") from err

    async def async_get_channel(self, channel_id: str) -> Channel:
        """Fetch name, logo and stream URLs for one channel."""
        data = await self._get(f"/items/{channel_id}")
        try:
            fields = data["customFields"]
            return Channel(
                id=str(data["id"]),
                title=data["title"],
                stream_url=fields["hlsURL"],
                stream_url_subtitles=fields.get("hlsWithSubtitlesURL"),
                logo=resize_image(data.get("images", {}).get("logo"), 512, 512),
            )
        except (KeyError, TypeError) as err:
            raise DRTVError(f"Unexpected channel data for {channel_id}") from err

    async def async_get_schedules(
        self, channel_ids: list[str], start: datetime, hours: int
    ) -> dict[str, list[Programme]]:
        """Fetch programmes overlapping [start hour, start hour + hours).

        `start` must be in UTC; DR interprets date/hour as UTC.
        """
        data = await self._get(
            "/schedules",
            {
                "date": start.strftime("%Y-%m-%d"),
                "hour": str(start.hour),
                "duration": str(hours),
                "channels": ",".join(channel_ids),
            },
        )
        result: dict[str, list[Programme]] = {}
        try:
            for channel in data:
                channel_id = str(channel["channelId"])
                result[channel_id] = [
                    _parse_programme(channel_id, entry)
                    for entry in channel.get("schedules", [])
                ]
        except (KeyError, TypeError, ValueError) as err:
            raise DRTVError("Unexpected schedule data") from err
        return result


def _parse_programme(channel_id: str, entry: dict[str, Any]) -> Programme:
    item = entry.get("item", {})
    images = item.get("images", {})
    return Programme(
        channel_id=channel_id,
        title=item.get("title") or "",
        description=item.get("shortDescription") or item.get("description"),
        start=datetime.fromisoformat(entry["startDate"]),
        end=datetime.fromisoformat(entry["endDate"]),
        image=resize_image(images.get("tile") or images.get("wallpaper"), 640, 360),
    )

"""Small async client for DR's (unofficial) TV and radio APIs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any

import aiohttp

from .const import API_BASE, API_PARAMS, RADIO_API_URL, RADIO_IMAGE_URL

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


@dataclass(frozen=True, slots=True)
class RadioStation:
    """A DR radio station (or a regional version of P4/P5)."""

    id: str
    title: str
    stream_url: str
    mime_type: str = "audio/mpeg"
    logo: str | None = None
    group_id: str | None = None  # "p4" for P4 Fyn etc.
    group_title: str | None = None


def resize_image(url: str | None, width: int, height: int) -> str | None:
    """DR image URLs default to 3000px; ask DR's resizer for a smaller one.

    DR's URLs also contain single quotes (Format='png'). Those break the
    unquoted CSS url() the Home Assistant frontend uses for media thumbnails,
    so they are percent-encoded, which DR accepts.
    """
    if url is None:
        return None
    url = _IMAGE_SIZE_RE.sub(f"Width={width}&Height={height}", url)
    return url.replace("'", "%27")


class DRTVClient:
    """Fetch channels and schedules from DR."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        """GET from the DRTV API."""
        return await self._get_url(
            f"{API_BASE}{path}", {**API_PARAMS, **(params or {})}
        )

    async def _get_url(self, url: str, params: dict[str, str] | None = None) -> Any:
        try:
            async with self._session.get(
                url, params=params, timeout=REQUEST_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except (TimeoutError, aiohttp.ClientError, ValueError) as err:
            raise DRTVError(f"Request to {url} failed: {err}") from err

    async def async_get_radio_stations(self) -> list[RadioStation]:
        """Fetch DR's radio stations, with P4/P5 split into regions."""
        data = await self._get_url(RADIO_API_URL)
        try:
            return parse_radio_stations(data)
        except (KeyError, TypeError, AttributeError) as err:
            raise DRTVError("Unexpected radio data") from err

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


def parse_radio_stations(data: list[dict[str, Any]]) -> list[RadioStation]:
    """Turn DR's radio channel list into playable stations.

    Only channels with an MP3 (ICY) stream are kept; that leaves out DR's
    internal web feeds, which only have HLS. P4 and P5 have no stream of
    their own but a list of regional "districts".
    """
    stations: list[RadioStation] = []
    for channel in sorted(data, key=lambda c: c.get("order", 0)):
        logo = _radio_logo(channel)
        if districts := channel.get("districts"):
            for district in districts:
                station = _radio_station(
                    district,
                    logo=_radio_logo(district) or logo,
                    group_id=channel["slug"],
                    group_title=channel["title"],
                )
                if station:
                    stations.append(station)
        elif station := _radio_station(channel, logo=logo):
            stations.append(station)
    return stations


def _radio_station(
    channel: dict[str, Any],
    logo: str | None,
    group_id: str | None = None,
    group_title: str | None = None,
) -> RadioStation | None:
    mp3 = sorted(
        (a for a in channel.get("audioAssets", []) if a.get("format") == "ICY"),
        key=lambda a: a.get("bitrate", 0),
        reverse=True,
    )
    if not mp3:
        return None
    return RadioStation(
        id=channel["slug"],
        title=channel["title"],
        stream_url=mp3[0]["url"],
        logo=logo,
        group_id=group_id,
        group_title=group_title,
    )


def _radio_logo(channel: dict[str, Any]) -> str | None:
    """Prefer the square image; DR serves it at 1080x1080 (~10 KB)."""
    images = channel.get("imageAssets", [])
    square = [i for i in images if i.get("ratio") == "1:1"]
    image = next(iter(square or images), None)
    return RADIO_IMAGE_URL.format(image_id=image["id"]) if image else None

"""Fixtures for DR TV tests."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.util import dt as dt_util
import pytest

from custom_components.dr_tv.const import API_BASE, FALLBACK_CHANNELS, RADIO_API_URL

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow loading custom_components/ in every test."""


def channel_payload(channel_id: str) -> dict[str, Any]:
    info = FALLBACK_CHANNELS[channel_id]
    return {
        "id": channel_id,
        "type": "channel",
        "title": info["title"],
        "images": {
            "logo": "https://img.example/logo?Format='png'&Width=2160&Height=2160"
        },
        "customFields": {
            "hlsURL": info["stream_url"],
            "hlsWithSubtitlesURL": info["stream_url"].replace("hls", "texthls"),
        },
    }


def schedule_payload() -> list[dict[str, Any]]:
    now = dt_util.utcnow().replace(second=0, microsecond=0)

    def entry(title: str, start: timedelta, end: timedelta) -> dict[str, Any]:
        return {
            "startDate": (now + start).isoformat().replace("+00:00", "Z"),
            "endDate": (now + end).isoformat().replace("+00:00", "Z"),
            "item": {
                "title": title,
                "shortDescription": f"About {title}",
                "images": {
                    "tile": f"https://img.example/{title}?Format='png'&Width=3000&Height=1688"
                },
            },
        }

    return [
        {
            "channelId": "20875",
            "schedules": [
                entry("Old show", timedelta(hours=-2), timedelta(minutes=-10)),
                entry("TV Avisen", timedelta(minutes=-10), timedelta(minutes=20)),
                entry("Aftenshowet", timedelta(minutes=20), timedelta(minutes=80)),
            ],
        },
        {
            "channelId": "20876",
            "schedules": [
                entry("Deadline", timedelta(minutes=-5), timedelta(minutes=25))
            ],
        },
    ]


def _icy(code: str) -> list[dict[str, Any]]:
    return [
        {"format": "HLS", "url": f"https://hls.example/{code}/master.m3u8"},
        {
            "format": "ICY",
            "bitrate": 128,
            "url": f"https://live-icy.dr.dk/A/{code}L.mp3",
        },
        {
            "format": "ICY",
            "bitrate": 192,
            "url": f"https://live-icy.dr.dk/A/{code}H.mp3",
        },
    ]


def _image(image_id: str) -> list[dict[str, Any]]:
    return [
        {"id": f"urn:dr:radio:image:{image_id}-wide", "ratio": "16:9"},
        {"id": f"urn:dr:radio:image:{image_id}", "ratio": "1:1"},
    ]


def radio_payload() -> list[dict[str, Any]]:
    """A trimmed copy of api.dr.dk/radio/v4/channels."""
    return [
        {
            "slug": "p4",
            "title": "P4",
            "order": 400,
            "imageAssets": _image("p4"),
            "districts": [
                {"slug": "p4fyn", "title": "P4 Fyn", "audioAssets": _icy("A07")},
                {
                    "slug": "p4kbh",
                    "title": "P4 København",
                    "audioAssets": _icy("A08"),
                    "imageAssets": _image("p4kbh"),
                },
            ],
        },
        {
            "slug": "p1",
            "title": "P1",
            "order": 100,
            "imageAssets": _image("p1"),
            "audioAssets": _icy("A03"),
        },
        # Internal web feed: HLS only, no MP3 -> not a station.
        {
            "slug": "dr-web-2",
            "title": "WEB2",
            "order": 900,
            "audioAssets": [{"format": "HLS", "url": "https://hls.example/web2.m3u8"}],
        },
        # No stream at all -> not a station.
        {"slug": "p7mix", "title": "P7 MIX", "order": 700, "imageAssets": _image("p7")},
    ]


@pytest.fixture
def mock_dr_api(aioclient_mock) -> Any:
    """Answer DR's API with canned data."""
    for channel_id in FALLBACK_CHANNELS:
        aioclient_mock.get(
            f"{API_BASE}/items/{channel_id}", json=channel_payload(channel_id)
        )
    aioclient_mock.get(f"{API_BASE}/schedules", json=schedule_payload())
    aioclient_mock.get(RADIO_API_URL, json=radio_payload())
    return aioclient_mock

"""Constants for the DR TV & Radio integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "dr"

# Where the dashboard card (and hls.js) are served from.
FRONTEND_URL: Final = "/dr"

API_BASE: Final = "https://production-cdn.dr-massive.com/api"
API_PARAMS: Final = {
    "device": "web_browser",
    "geoLocation": "dk",
    "isDeviceAbroad": "false",
}

# How often the programme schedule is refreshed.
SCAN_INTERVAL: Final = timedelta(minutes=5)
# How often channel metadata (names, logos, stream URLs) is refreshed.
CHANNEL_REFRESH_INTERVAL: Final = timedelta(hours=6)
# Hours of schedule to fetch per refresh (starting at the current UTC hour).
SCHEDULE_WINDOW_HOURS: Final = 4
# Consecutive failed refreshes before a repair issue is raised.
FAILURES_BEFORE_ISSUE: Final = 3

ISSUE_API_UNAVAILABLE: Final = "api_unavailable"

# DR does not expose a public channel list, so the known live channels are
# listed here. They also serve as a fallback when DR's API is unreachable:
# streams keep working, only the programme info is missing.
FALLBACK_CHANNELS: Final[dict[str, dict[str, str]]] = {
    "20875": {
        "slug": "dr1",
        "title": "DR1",
        "stream_url": "https://drlivedr1hls.akamaized.net/hls/live/2113625/drlivedr1/master.m3u8",
    },
    "20876": {
        "slug": "dr2",
        "title": "DR2",
        "stream_url": "https://drlivedr2hls.akamaized.net/hls/live/2113623/drlivedr2/master.m3u8",
    },
    "20892": {
        "slug": "ramasjang",
        "title": "DR Ramasjang",
        "stream_url": "https://drlivedrrhls.akamaized.net/hls/live/2113621/drlivedrr/master.m3u8",
    },
    "192099": {
        "slug": "tva",
        "title": "TVA Live",
        "stream_url": "https://drlivedrtvahls.akamaized.net/hls/live/2113613/drlivedrtva/master.m3u8",
    },
    "192100": {
        "slug": "drtv-ekstra",
        "title": "DRTV Ekstra",
        "stream_url": "https://drlivedrtvbhls.akamaized.net/hls/live/2113611/drlivedrtvb/master.m3u8",
    },
}

RADIO_API_URL: Final = "https://api.dr.dk/radio/v4/channels"
RADIO_IMAGE_URL: Final = "https://asset.dr.dk/drlyd/images/{image_id}"

# Built-in radio stations, used until (or if) DR's radio API answers:
# (id, title, MP3 stream, group id, group title). P4 and P5 are regional.
FALLBACK_RADIO: Final[list[tuple[str, str, str, str | None, str | None]]] = [
    ("ly1", "LYD ekstra", "https://live-icy.dr.dk/A/A27H.mp3", None, None),
    ("ly2", "LYD ekstra 2", "https://live-icy.dr.dk/A/A21H.mp3", None, None),
    ("p1", "P1", "https://live-icy.dr.dk/A/A03H.mp3", None, None),
    ("p2", "P2", "https://live-icy.dr.dk/A/A04H.mp3", None, None),
    ("p3", "P3", "https://live-icy.dr.dk/A/A05H.mp3", None, None),
    ("p4bornholm", "P4 Bornholm", "https://live-icy.dr.dk/A/A06H.mp3", "p4", "P4"),
    ("p4esbjerg", "P4 Esbjerg", "https://live-icy.dr.dk/A/A15H.mp3", "p4", "P4"),
    ("p4fyn", "P4 Fyn", "https://live-icy.dr.dk/A/A07H.mp3", "p4", "P4"),
    ("p4kbh", "P4 København", "https://live-icy.dr.dk/A/A08H.mp3", "p4", "P4"),
    ("p4vest", "P4 Midt & Vest", "https://live-icy.dr.dk/A/A09H.mp3", "p4", "P4"),
    ("p4nord", "P4 Nordjylland", "https://live-icy.dr.dk/A/A10H.mp3", "p4", "P4"),
    ("p4sjaelland", "P4 Sjælland", "https://live-icy.dr.dk/A/A11H.mp3", "p4", "P4"),
    ("p4syd", "P4 Syd", "https://live-icy.dr.dk/A/A12H.mp3", "p4", "P4"),
    ("p4trekanten", "P4 Trekanten", "https://live-icy.dr.dk/A/A13H.mp3", "p4", "P4"),
    ("p4aarhus", "P4 Østjylland", "https://live-icy.dr.dk/A/A14H.mp3", "p4", "P4"),
    ("p5bornholm", "P5 Bornholm", "https://live-icy.dr.dk/A/A30H.mp3", "p5", "P5"),
    ("p5esbjerg", "P5 Esbjerg", "https://live-icy.dr.dk/A/A26H.mp3", "p5", "P5"),
    ("p5fyn", "P5 Fyn", "https://live-icy.dr.dk/A/A02H.mp3", "p5", "P5"),
    ("p5kbh", "P5 København", "https://live-icy.dr.dk/A/A28H.mp3", "p5", "P5"),
    ("p5vest", "P5 Midt & Vest", "https://live-icy.dr.dk/A/A17H.mp3", "p5", "P5"),
    ("p5nord", "P5 Nordjylland", "https://live-icy.dr.dk/A/A18H.mp3", "p5", "P5"),
    ("p5sjaelland", "P5 Sjælland", "https://live-icy.dr.dk/A/A19H.mp3", "p5", "P5"),
    ("p5syd", "P5 Syd", "https://live-icy.dr.dk/A/A20H.mp3", "p5", "P5"),
    ("p5trekanten", "P5 Trekanten", "https://live-icy.dr.dk/A/A23L.mp3", "p5", "P5"),
    ("p5aarhus", "P5 Østjylland", "https://live-icy.dr.dk/A/A24L.mp3", "p5", "P5"),
    ("p6beat", "P6", "https://live-icy.dr.dk/A/A29H.mp3", None, None),
    ("p8jazz", "P8", "https://live-icy.dr.dk/A/A22H.mp3", None, None),
]

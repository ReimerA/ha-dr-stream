"""Constants for the DR TV integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "dr_tv"

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
        "title": "DR1",
        "stream_url": "https://drlivedr1hls.akamaized.net/hls/live/2113625/drlivedr1/master.m3u8",
    },
    "20876": {
        "title": "DR2",
        "stream_url": "https://drlivedr2hls.akamaized.net/hls/live/2113623/drlivedr2/master.m3u8",
    },
    "20892": {
        "title": "DR Ramasjang",
        "stream_url": "https://drlivedrrhls.akamaized.net/hls/live/2113621/drlivedrr/master.m3u8",
    },
    "192099": {
        "title": "TVA Live",
        "stream_url": "https://drlivedrtvahls.akamaized.net/hls/live/2113613/drlivedrtva/master.m3u8",
    },
    "192100": {
        "title": "DRTV Ekstra",
        "stream_url": "https://drlivedrtvbhls.akamaized.net/hls/live/2113611/drlivedrtvb/master.m3u8",
    },
}

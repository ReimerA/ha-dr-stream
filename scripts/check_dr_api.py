"""Check that DR's real APIs still deliver what the integration relies on.

Run from the repository root:  python scripts/check_dr_api.py
Exits non-zero (and says why) when something is missing or has changed.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
import sys

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.dr.api import DRTVClient
from custom_components.dr.const import (
    FALLBACK_CHANNELS,
    FALLBACK_RADIO,
)


async def main() -> list[str]:
    problems: list[str] = []
    async with aiohttp.ClientSession() as session:
        client = DRTVClient(session)

        for channel_id, info in FALLBACK_CHANNELS.items():
            try:
                channel = await client.async_get_channel(channel_id)
            except Exception as err:  # noqa: BLE001 - report every failure
                problems.append(f"TV channel {info['title']}: {err}")
                continue
            if channel.stream_url != info["stream_url"]:
                problems.append(
                    f"TV channel {channel.title}: stream URL changed to "
                    f"{channel.stream_url} (update FALLBACK_CHANNELS)"
                )
            print(f"ok  TV    {channel.title}")

        try:
            schedules = await client.async_get_schedules(
                list(FALLBACK_CHANNELS), datetime.now(UTC), 4
            )
        except Exception as err:  # noqa: BLE001
            problems.append(f"TV schedule: {err}")
        else:
            with_programmes = [cid for cid, p in schedules.items() if p]
            if not with_programmes:
                problems.append("TV schedule: no programmes for any channel")
            print(f"ok  TV    schedule for {len(with_programmes)} channels")

        try:
            stations = {s.id: s for s in await client.async_get_radio_stations()}
        except Exception as err:  # noqa: BLE001
            problems.append(f"Radio stations: {err}")
        else:
            for station_id, title, url, _, _ in FALLBACK_RADIO:
                station = stations.get(station_id)
                if station is None:
                    problems.append(f"Radio {title}: missing from DR's list")
                elif station.stream_url != url:
                    problems.append(
                        f"Radio {title}: stream URL changed to "
                        f"{station.stream_url} (update FALLBACK_RADIO)"
                    )
            print(f"ok  Radio {len(stations)} stations")

    return problems


if __name__ == "__main__":
    found = asyncio.run(main())
    for problem in found:
        print(f"::error::{problem}")
    sys.exit(1 if found else 0)

"""Check that DR's real APIs still deliver what the integration relies on.

Run from the repository root:  python scripts/check_dr_api.py
Exits non-zero (and says why) when something is missing or a built-in
fallback stream no longer plays. A fallback that differs from what DR returns
but still plays is only a warning: DR moves streams gradually, and the
integration uses whatever URL DR returns.
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

STREAM_TIMEOUT = aiohttp.ClientTimeout(total=15)


async def stream_plays(session: aiohttp.ClientSession, url: str) -> bool:
    """Return True if the URL answers with the start of an HLS or MP3 stream."""
    try:
        async with session.get(
            url, timeout=STREAM_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"}
        ) as resp:
            if resp.status != 200:
                return False
            # Radio streams never end, so read only the first bytes.
            head = await resp.content.read(512)
    except (TimeoutError, aiohttp.ClientError):
        return False
    if url.endswith(".m3u8"):
        return head.startswith(b"#EXTM3U")
    return bool(head)


async def check_fallback(
    session: aiohttp.ClientSession,
    name: str,
    fallback: str,
    current: str,
    constant: str,
    problems: list[str],
    warnings: list[str],
) -> None:
    """Fail if the fallback URL is dead, warn if it merely differs from DR's."""
    if fallback == current:
        return
    if await stream_plays(session, fallback):
        warnings.append(
            f"{name}: DR now returns {current}; the fallback still plays "
            f"(consider updating {constant})"
        )
    else:
        problems.append(
            f"{name}: fallback stream {fallback} no longer plays; DR returns "
            f"{current} (update {constant})"
        )


async def main() -> tuple[list[str], list[str]]:
    problems: list[str] = []
    warnings: list[str] = []
    async with aiohttp.ClientSession() as session:
        client = DRTVClient(session)

        for channel_id, info in FALLBACK_CHANNELS.items():
            try:
                channel = await client.async_get_channel(channel_id)
            except Exception as err:  # noqa: BLE001 - report every failure
                problems.append(f"TV channel {info['title']}: {err}")
                continue
            await check_fallback(
                session,
                f"TV channel {channel.title}",
                info["stream_url"],
                channel.stream_url,
                "FALLBACK_CHANNELS",
                problems,
                warnings,
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
            # DR has started asking for an API key on some of its servers, so
            # the list often fails. The integration then uses FALLBACK_RADIO,
            # so this only warns, but those streams must still play.
            warnings.append(f"Radio stations: {err} (using FALLBACK_RADIO)")
            dead = [
                (title, url)
                for _, title, url, _, _ in FALLBACK_RADIO
                if not await stream_plays(session, url)
            ]
            for title, url in dead:
                problems.append(
                    f"Radio {title}: fallback stream {url} no longer plays "
                    "(update FALLBACK_RADIO)"
                )
            print(f"ok  Radio {len(FALLBACK_RADIO) - len(dead)} fallback streams play")
        else:
            for station_id, title, url, _, _ in FALLBACK_RADIO:
                station = stations.get(station_id)
                if station is None:
                    problems.append(f"Radio {title}: missing from DR's list")
                else:
                    await check_fallback(
                        session,
                        f"Radio {title}",
                        url,
                        station.stream_url,
                        "FALLBACK_RADIO",
                        problems,
                        warnings,
                    )
            print(f"ok  Radio {len(stations)} stations")

    return problems, warnings


if __name__ == "__main__":
    found, warned = asyncio.run(main())
    for warning in warned:
        print(f"::warning::{warning}")
    for problem in found:
        print(f"::error::{problem}")
    sys.exit(1 if found else 0)

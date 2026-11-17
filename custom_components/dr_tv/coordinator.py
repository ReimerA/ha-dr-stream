"""Data update coordinator for DR TV and DR Radio."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import Channel, DRTVClient, DRTVError, Programme, RadioStation
from .const import (
    CHANNEL_REFRESH_INTERVAL,
    DOMAIN,
    FAILURES_BEFORE_ISSUE,
    FALLBACK_CHANNELS,
    FALLBACK_RADIO,
    ISSUE_API_UNAVAILABLE,
    SCAN_INTERVAL,
    SCHEDULE_WINDOW_HOURS,
)

_LOGGER = logging.getLogger(__name__)

type DRTVConfigEntry = ConfigEntry[DRTVCoordinator]


@dataclass
class DRTVData:
    """Everything the card and the Media panel need."""

    channels: dict[str, Channel]
    schedules: dict[str, list[Programme]] = field(default_factory=dict)
    radio: dict[str, RadioStation] = field(default_factory=dict)

    def now_playing(
        self, channel_id: str, now: datetime | None = None
    ) -> Programme | None:
        """Return the programme on air on a channel right now."""
        now = now or dt_util.utcnow()
        for programme in self.schedules.get(channel_id, []):
            if programme.start <= now < programme.end:
                return programme
        return None

    def up_next(self, channel_id: str, now: datetime | None = None) -> Programme | None:
        """Return the next programme to start on a channel."""
        now = now or dt_util.utcnow()
        upcoming = [p for p in self.schedules.get(channel_id, []) if p.start > now]
        return min(upcoming, key=lambda p: p.start, default=None)


def fallback_channels() -> dict[str, Channel]:
    """Hard-coded channels, used until (or if) DR's API answers."""
    return {
        channel_id: Channel(id=channel_id, **info)
        for channel_id, info in FALLBACK_CHANNELS.items()
    }


def fallback_radio() -> dict[str, RadioStation]:
    """Hard-coded radio stations, used until (or if) DR's radio API answers."""
    return {
        station_id: RadioStation(
            id=station_id,
            title=title,
            stream_url=url,
            group_id=group_id,
            group_title=group_title,
        )
        for station_id, title, url, group_id, group_title in FALLBACK_RADIO
    }


class DRTVCoordinator(DataUpdateCoordinator[DRTVData]):
    """Fetch channels and schedules from DR.

    When DR is unreachable the last known data (or the hard-coded channel
    list) is kept, so entities stay usable. After repeated failures a repair
    issue tells the user what is going on.
    """

    config_entry: DRTVConfigEntry

    def __init__(self, hass: HomeAssistant, entry: DRTVConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = DRTVClient(async_get_clientsession(hass))
        self._channels: dict[str, Channel] = fallback_channels()
        self._channels_fetched: datetime | None = None
        self._radio: dict[str, RadioStation] = fallback_radio()
        self._radio_fetched: datetime | None = None
        self._failures = 0

    async def _async_update_data(self) -> DRTVData:
        now = dt_util.utcnow()
        await self._async_refresh_channels(now)
        await self._async_refresh_radio(now)

        try:
            schedules = await self.client.async_get_schedules(
                list(self._channels), now, SCHEDULE_WINDOW_HOURS
            )
        except DRTVError as err:
            self._record_failure(err)
            previous = self.data.schedules if self.data else {}
            return DRTVData(self._channels, previous, self._radio)

        self._record_success()
        return DRTVData(self._channels, schedules, self._radio)

    async def _async_refresh_radio(self, now: datetime) -> None:
        if (
            self._radio_fetched is not None
            and now - self._radio_fetched < CHANNEL_REFRESH_INTERVAL
        ):
            return
        try:
            stations = await self.client.async_get_radio_stations()
        except DRTVError as err:
            _LOGGER.debug("Keeping known radio stations: %s", err)
            return
        if stations:
            self._radio = {station.id: station for station in stations}
            self._radio_fetched = now

    async def _async_refresh_channels(self, now: datetime) -> None:
        if (
            self._channels_fetched is not None
            and now - self._channels_fetched < CHANNEL_REFRESH_INTERVAL
        ):
            return
        ids = list(FALLBACK_CHANNELS)
        results = await asyncio.gather(
            *(self.client.async_get_channel(cid) for cid in ids),
            return_exceptions=True,
        )
        ok = 0
        for channel_id, result in zip(ids, results, strict=True):
            if isinstance(result, Channel):
                self._channels[channel_id] = result
                ok += 1
            else:
                _LOGGER.debug(
                    "Keeping known data for channel %s: %s", channel_id, result
                )
        if ok:
            self._channels_fetched = now

    def _record_failure(self, err: DRTVError) -> None:
        self._failures += 1
        _LOGGER.warning(
            "Could not fetch DR schedule (attempt %s), keeping last known data: %s",
            self._failures,
            err,
        )
        if self._failures == FAILURES_BEFORE_ISSUE:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                ISSUE_API_UNAVAILABLE,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_API_UNAVAILABLE,
                translation_placeholders={"error": str(err)},
            )

    def _record_success(self) -> None:
        if self._failures >= FAILURES_BEFORE_ISSUE:
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_API_UNAVAILABLE)
        self._failures = 0

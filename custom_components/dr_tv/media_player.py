"""Media player entity for DR TV.

The entity does not output audio or video itself. It holds the selected
channel and exposes what is on air plus the channel's stream URL, so standard
media cards (and a video card or cast action) can use it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import Channel, Programme
from .const import DOMAIN
from .coordinator import DRTVConfigEntry, DRTVCoordinator

ATTR_STREAM_URL = "stream_url"
ATTR_STREAM_URL_SUBTITLES = "stream_url_subtitles"
ATTR_DESCRIPTION = "description"
ATTR_NEXT_TITLE = "next_title"
ATTR_NEXT_START = "next_start"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DRTVConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the DR TV media player."""
    async_add_entities([DRTVMediaPlayer(entry.runtime_data)])


class DRTVMediaPlayer(
    CoordinatorEntity[DRTVCoordinator], MediaPlayerEntity, RestoreEntity
):
    """One player for all DR channels; the channels are its sources."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_media_content_type = MediaType.CHANNEL
    _attr_media_image_remotely_accessible = True
    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: DRTVCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_player"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="DR TV",
            manufacturer="DR",
            entry_type=DeviceEntryType.SERVICE,
        )
        self._channel_id: str | None = next(iter(coordinator.data.channels), None)
        self._is_on = True
        self._unsub_programme_end: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the last selected channel and on/off state."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._is_on = last.state != MediaPlayerState.OFF
            if (
                channel := self._channel_by_title(last.attributes.get("source"))
            ) is not None:
                self._channel_id = channel.id
        self._schedule_programme_end()
        self.async_on_remove(self._cancel_programme_end)

    # --- helpers -----------------------------------------------------------

    @property
    def _channel(self) -> Channel | None:
        if self._channel_id is None:
            return None
        return self.coordinator.data.channels.get(self._channel_id)

    @property
    def _programme(self) -> Programme | None:
        if self._channel_id is None:
            return None
        return self.coordinator.data.now_playing(self._channel_id)

    def _channel_by_title(self, title: str | None) -> Channel | None:
        return next(
            (c for c in self.coordinator.data.channels.values() if c.title == title),
            None,
        )

    def _cancel_programme_end(self) -> None:
        if self._unsub_programme_end is not None:
            self._unsub_programme_end()
            self._unsub_programme_end = None

    @callback
    def _schedule_programme_end(self) -> None:
        """Update state exactly when the current programme ends."""
        self._cancel_programme_end()
        if (programme := self._programme) is None:
            return

        @callback
        def _programme_ended(_now: datetime) -> None:
            self._unsub_programme_end = None
            self._schedule_programme_end()
            self.async_write_ha_state()

        self._unsub_programme_end = async_track_point_in_utc_time(
            self.hass, _programme_ended, programme.end
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        self._schedule_programme_end()
        super()._handle_coordinator_update()

    # --- state -------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Stay available on fallback data; DR being down is a repair issue."""
        return self.coordinator.data is not None

    @property
    def state(self) -> MediaPlayerState:
        return MediaPlayerState.PLAYING if self._is_on else MediaPlayerState.OFF

    @property
    def source_list(self) -> list[str]:
        return [c.title for c in self.coordinator.data.channels.values()]

    @property
    def source(self) -> str | None:
        return channel.title if (channel := self._channel) else None

    @property
    def media_channel(self) -> str | None:
        return self.source

    @property
    def media_content_id(self) -> str | None:
        return channel.stream_url if (channel := self._channel) else None

    @property
    def media_title(self) -> str | None:
        if (programme := self._programme) is not None:
            return programme.title
        return self.source

    @property
    def media_image_url(self) -> str | None:
        if (programme := self._programme) is not None and programme.image:
            return programme.image
        return channel.logo if (channel := self._channel) else None

    @property
    def media_duration(self) -> int | None:
        if (programme := self._programme) is None:
            return None
        return int((programme.end - programme.start).total_seconds())

    @property
    def media_position(self) -> int | None:
        if (programme := self._programme) is None:
            return None
        return int((dt_util.utcnow() - programme.start).total_seconds())

    @property
    def media_position_updated_at(self) -> datetime | None:
        return dt_util.utcnow() if self._programme is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        channel = self._channel
        programme = self._programme
        up_next = (
            self.coordinator.data.up_next(self._channel_id)
            if self._channel_id
            else None
        )
        return {
            ATTR_STREAM_URL: channel.stream_url if channel else None,
            ATTR_STREAM_URL_SUBTITLES: channel.stream_url_subtitles
            if channel
            else None,
            ATTR_DESCRIPTION: programme.description if programme else None,
            ATTR_NEXT_TITLE: up_next.title if up_next else None,
            ATTR_NEXT_START: up_next.start.isoformat() if up_next else None,
        }

    # --- commands ----------------------------------------------------------

    async def async_select_source(self, source: str) -> None:
        """Switch channel."""
        if (channel := self._channel_by_title(source)) is None:
            raise ServiceValidationError(f"Unknown DR channel: {source}")
        self._channel_id = channel.id
        self._is_on = True
        self._schedule_programme_end()
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        self._is_on = False
        self.async_write_ha_state()

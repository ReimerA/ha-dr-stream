"""Expose DR's live channels in Home Assistant's Media panel.

From there a channel can be played on any player that handles HLS, such as a
Chromecast, a smart TV or the browser itself.
"""

from __future__ import annotations

from homeassistant.components.media_player import BrowseError, MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant

from .api import Channel
from .const import DOMAIN
from .coordinator import DRTVConfigEntry, DRTVData, fallback_channels

# The frontend only uses its HLS player for exactly this spelling; the more
# official "application/vnd.apple.mpegurl" gives "media not supported".
HLS_MIME_TYPE = "application/x-mpegURL"


async def async_get_media_source(hass: HomeAssistant) -> DRTVMediaSource:
    """Set up the DR TV media source."""
    return DRTVMediaSource(hass)


class DRTVMediaSource(MediaSource):
    """DR live channels as a media source."""

    name = "DR TV"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    def _data(self) -> DRTVData | None:
        entries: list[DRTVConfigEntry] = self.hass.config_entries.async_loaded_entries(
            DOMAIN
        )
        return entries[0].runtime_data.data if entries else None

    def _channels(self) -> dict[str, Channel]:
        data = self._data()
        return data.channels if data else fallback_channels()

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Turn a channel id into its HLS stream."""
        if (channel := self._channels().get(item.identifier)) is None:
            raise Unresolvable(f"Unknown DR channel: {item.identifier}")
        return PlayMedia(channel.stream_url, HLS_MIME_TYPE)

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """List the live channels."""
        if item.identifier:
            raise BrowseError("DR TV has no nested folders")
        data = self._data()
        children = []
        for channel in self._channels().values():
            programme = data.now_playing(channel.id) if data else None
            title = (
                f"{channel.title}: {programme.title}" if programme else channel.title
            )
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=channel.id,
                    media_class=MediaClass.CHANNEL,
                    media_content_type=MediaType.CHANNEL,
                    title=title,
                    can_play=True,
                    can_expand=False,
                    thumbnail=(programme.image if programme else None) or channel.logo,
                )
            )
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.CHANNELS,
            title="DR TV",
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.CHANNEL,
            children=children,
        )

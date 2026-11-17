"""DR's live TV channels and radio stations in Home Assistant's Media panel.

Layout (media-source://dr_tv/<identifier>):

    DR                      ""
    ├── DR TV               "tv"
    │   └── DR1 …           "tv/20875"
    └── DR Radio            "radio"
        ├── P1 …            "radio/p1"
        └── P4              "radio/group/p4"
            └── P4 Fyn …    "radio/p4fyn"

TV plays as HLS video, radio as MP3, on any player that supports them
(the browser, Chromecast, Sonos, smart TVs, ...).
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

from .api import Channel, RadioStation
from .const import DOMAIN
from .coordinator import DRTVConfigEntry, DRTVData, fallback_channels, fallback_radio

# The frontend only uses its HLS player for exactly this spelling; the more
# official "application/vnd.apple.mpegurl" gives "media not supported".
HLS_MIME_TYPE = "application/x-mpegURL"

TV = "tv"
RADIO = "radio"
RADIO_GROUP = "radio/group/"


async def async_get_media_source(hass: HomeAssistant) -> DRTVMediaSource:
    """Set up the DR media source."""
    return DRTVMediaSource(hass)


class DRTVMediaSource(MediaSource):
    """DR live TV and radio as a media source."""

    name = "DR"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    # --- data ------------------------------------------------------------------

    def _data(self) -> DRTVData | None:
        entries: list[DRTVConfigEntry] = self.hass.config_entries.async_loaded_entries(
            DOMAIN
        )
        return entries[0].runtime_data.data if entries else None

    def _channels(self) -> dict[str, Channel]:
        data = self._data()
        return data.channels if data else fallback_channels()

    def _radio(self) -> dict[str, RadioStation]:
        data = self._data()
        return data.radio if data and data.radio else fallback_radio()

    # --- playing ---------------------------------------------------------------

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Turn a channel or station into its stream."""
        kind, _, item_id = (item.identifier or "").rpartition("/")
        # "20875" without a prefix is how TV channels were addressed before
        # radio was added; keep it working for existing automations.
        if kind in ("", TV) and (channel := self._channels().get(item_id)):
            return PlayMedia(channel.stream_url, HLS_MIME_TYPE)
        if kind == RADIO and (station := self._radio().get(item_id)):
            return PlayMedia(station.stream_url, station.mime_type)
        raise Unresolvable(f"Unknown DR channel or station: {item.identifier}")

    # --- browsing --------------------------------------------------------------

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse DR TV and DR Radio."""
        identifier = item.identifier or ""
        if identifier == "":
            return self._browse_root()
        if identifier == TV:
            return self._browse_tv()
        if identifier == RADIO:
            return self._browse_radio()
        if identifier.startswith(RADIO_GROUP):
            return self._browse_radio_group(identifier.removeprefix(RADIO_GROUP))
        raise BrowseError(f"Unknown DR folder: {identifier}")

    def _browse_root(self) -> BrowseMediaSource:
        return _folder(
            None,
            "DR",
            MediaClass.DIRECTORY,
            [
                _folder(TV, "DR TV", MediaClass.CHANNEL),
                _folder(RADIO, "DR Radio", MediaClass.MUSIC),
            ],
        )

    def _browse_tv(self) -> BrowseMediaSource:
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
                    identifier=f"{TV}/{channel.id}",
                    media_class=MediaClass.CHANNEL,
                    media_content_type=MediaType.CHANNEL,
                    title=title,
                    can_play=True,
                    can_expand=False,
                    thumbnail=(programme.image if programme else None) or channel.logo,
                )
            )
        return _folder(TV, "DR TV", MediaClass.CHANNEL, children)

    def _browse_radio(self) -> BrowseMediaSource:
        children: list[BrowseMediaSource] = []
        groups_seen: set[str] = set()
        for station in self._radio().values():
            if station.group_id is None:
                children.append(_station(station))
            elif station.group_id not in groups_seen:
                # Regional channels (P4, P5) become one folder each, in the
                # position of their first region.
                groups_seen.add(station.group_id)
                folder = _folder(
                    f"{RADIO_GROUP}{station.group_id}",
                    station.group_title or station.group_id,
                    MediaClass.MUSIC,
                )
                folder.thumbnail = station.logo
                children.append(folder)
        return _folder(RADIO, "DR Radio", MediaClass.MUSIC, children)

    def _browse_radio_group(self, group_id: str) -> BrowseMediaSource:
        stations = [s for s in self._radio().values() if s.group_id == group_id]
        if not stations:
            raise BrowseError(f"Unknown DR radio group: {group_id}")
        return _folder(
            f"{RADIO_GROUP}{group_id}",
            stations[0].group_title or group_id,
            MediaClass.MUSIC,
            [_station(s) for s in stations],
        )


def _folder(
    identifier: str | None,
    title: str,
    children_class: MediaClass,
    children: list[BrowseMediaSource] | None = None,
) -> BrowseMediaSource:
    return BrowseMediaSource(
        domain=DOMAIN,
        identifier=identifier,
        media_class=MediaClass.DIRECTORY,
        media_content_type=MediaType.CHANNELS,
        title=title,
        can_play=False,
        can_expand=True,
        children_media_class=children_class,
        children=children,
    )


def _station(station: RadioStation) -> BrowseMediaSource:
    return BrowseMediaSource(
        domain=DOMAIN,
        identifier=f"{RADIO}/{station.id}",
        media_class=MediaClass.MUSIC,
        media_content_type=station.mime_type,
        title=station.title,
        can_play=True,
        can_expand=False,
        thumbnail=station.logo,
    )

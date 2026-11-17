"""Websocket API used by the DR TV dashboard card."""

from __future__ import annotations

from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .api import Programme
from .const import DOMAIN
from .coordinator import DRTVConfigEntry


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register the websocket commands."""
    websocket_api.async_register_command(hass, ws_channels)


def _programme(programme: Programme | None) -> dict[str, Any] | None:
    if programme is None:
        return None
    return {
        "title": programme.title,
        "description": programme.description,
        "start": programme.start.isoformat(),
        "end": programme.end.isoformat(),
        "image": programme.image,
    }


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/channels"})
@callback
def ws_channels(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return DR's live channels with what is on now and next."""
    entries: list[DRTVConfigEntry] = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], "not_loaded", "DR TV is not set up")
        return
    data = entries[0].runtime_data.data
    now = dt_util.utcnow()
    connection.send_result(
        msg["id"],
        {
            "channels": [
                {
                    "id": channel.id,
                    "title": channel.title,
                    "logo": channel.logo,
                    "stream_url": channel.stream_url,
                    "stream_url_subtitles": channel.stream_url_subtitles,
                    "now": _programme(data.now_playing(channel.id, now)),
                    "next": _programme(data.up_next(channel.id, now)),
                }
                for channel in data.channels.values()
            ]
        },
    )

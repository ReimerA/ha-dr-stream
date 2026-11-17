"""The DR TV integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import DOMAIN, FRONTEND_URL
from .coordinator import DRTVConfigEntry, DRTVCoordinator
from .websocket import async_register_websocket_commands

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the dashboard card and register the websocket API (once)."""
    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_URL, str(Path(__file__).parent / "frontend"), False)]
    )
    # Loads the card on every dashboard, so no manual "resource" is needed.
    # The version in the URL makes browsers fetch the new card after updates.
    add_extra_js_url(hass, f"{FRONTEND_URL}/dr-tv-card.js?v={integration.version}")
    async_register_websocket_commands(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DRTVConfigEntry) -> bool:
    """Set up DR TV from a config entry."""
    coordinator = DRTVCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # A coordinator only polls while something listens to it. There are no
    # entities, so keep it polling for the card and the Media panel.
    entry.async_on_unload(coordinator.async_add_listener(lambda: None))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DRTVConfigEntry) -> bool:
    """Unload a config entry."""
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: DRTVConfigEntry) -> bool:
    """Migrate old config entries."""
    if entry.version == 1:
        # Version 1 had a media_player entity (and its device); it is gone.
        ent_reg = er.async_get(hass)
        for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            ent_reg.async_remove(entity.entity_id)
        dev_reg = dr.async_get(hass)
        for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
            dev_reg.async_remove_device(device.id)
        hass.config_entries.async_update_entry(entry, version=2)
        _LOGGER.info("Removed the old DR TV media player; use the DR TV card instead")
    return True

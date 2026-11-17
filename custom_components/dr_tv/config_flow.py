"""Config flow for DR TV."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class DRTVConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add DR TV from the UI. There is nothing to configure."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding the integration."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="DR TV", data={})
        return self.async_show_form(step_id="user")

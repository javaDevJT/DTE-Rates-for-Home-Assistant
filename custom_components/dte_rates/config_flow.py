from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_NET_METERING, CONF_SELECTED_RATE, DOMAIN
from .coordinator import DteRateCoordinator


class DteRatesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        coordinator = DteRateCoordinator(self.hass)
        await coordinator.async_refresh()
        if coordinator.data is None:
            return self.async_abort(reason="cannot_connect")

        rate_options = {
            code: f"{rate.name} ({code})"
            for code, rate in coordinator.data.rates.items()
        }

        if user_input is not None:
            selected_rate = user_input[CONF_SELECTED_RATE]
            return self.async_create_entry(
                title=rate_options[selected_rate],
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_SELECTED_RATE): vol.In(rate_options),
                vol.Optional(CONF_NET_METERING, default=False): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

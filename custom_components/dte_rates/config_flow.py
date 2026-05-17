from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_INCLUDE_PSCR,
    CONF_NET_METERING,
    CONF_SELECTED_RATE,
    CONF_TAX_RATE,
    DEFAULT_INCLUDE_PSCR,
    DEFAULT_TAX_RATE_PERCENT,
    DOMAIN,
)
from .coordinator import DteRateCoordinator
from .settings import normalize_tax_rate_percent


class DteRatesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry) -> config_entries.OptionsFlow:
        return DteRatesOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        coordinator = DteRateCoordinator(self.hass)
        await coordinator.async_refresh()
        if coordinator.data is None:
            return self.async_abort(reason="cannot_connect")

        rate_options = {
            code: f"{rate.name} ({code})"
            for code, rate in coordinator.data.rates.items()
        }

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                data = _normalize_config_input(user_input)
            except ValueError:
                errors["base"] = "invalid_tax_rate"
            else:
                selected_rate = data[CONF_SELECTED_RATE]
                return self.async_create_entry(
                    title=rate_options[selected_rate],
                    data=data,
                )

        schema = _user_schema(rate_options)
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "rider18_status": _rider18_status(coordinator.data),
                "tax_note": _tax_note(),
            },
        )


class DteRatesOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                data = _normalize_options_input(user_input)
            except ValueError:
                errors["base"] = "invalid_tax_rate"
            else:
                return self.async_create_entry(title="", data=data)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self.config_entry),
            errors=errors,
            description_placeholders={"tax_note": _tax_note()},
        )


def _normalize_config_input(user_input: dict) -> dict:
    data = dict(user_input)
    data.setdefault(CONF_INCLUDE_PSCR, DEFAULT_INCLUDE_PSCR)
    data.setdefault(CONF_TAX_RATE, DEFAULT_TAX_RATE_PERCENT)
    data[CONF_INCLUDE_PSCR] = bool(data[CONF_INCLUDE_PSCR])
    data[CONF_TAX_RATE] = normalize_tax_rate_percent(data[CONF_TAX_RATE])
    return data


def _normalize_options_input(user_input: dict) -> dict:
    data = {
        CONF_INCLUDE_PSCR: bool(user_input.get(CONF_INCLUDE_PSCR, DEFAULT_INCLUDE_PSCR)),
        CONF_TAX_RATE: normalize_tax_rate_percent(user_input.get(CONF_TAX_RATE, DEFAULT_TAX_RATE_PERCENT)),
    }
    return data


def _user_schema(rate_options: dict[str, str]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_SELECTED_RATE): vol.In(rate_options),
            vol.Optional(CONF_NET_METERING, default=False): bool,
            vol.Optional(CONF_INCLUDE_PSCR, default=DEFAULT_INCLUDE_PSCR): bool,
            vol.Optional(CONF_TAX_RATE, default=DEFAULT_TAX_RATE_PERCENT): str,
        }
    )


def _options_schema(config_entry) -> vol.Schema:
    options = getattr(config_entry, "options", None) or {}
    data = getattr(config_entry, "data", None) or {}
    include_pscr = options.get(CONF_INCLUDE_PSCR, data.get(CONF_INCLUDE_PSCR, DEFAULT_INCLUDE_PSCR))
    tax_rate = options.get(CONF_TAX_RATE, data.get(CONF_TAX_RATE, DEFAULT_TAX_RATE_PERCENT))
    return vol.Schema(
        {
            vol.Optional(CONF_INCLUDE_PSCR, default=include_pscr): bool,
            vol.Optional(CONF_TAX_RATE, default=tax_rate): str,
        }
    )


def _rider18_status(rate_card) -> str:
    count = len(getattr(rate_card, "pscr_rates", {}))
    if count:
        suffix = "tariff" if count == 1 else "tariffs"
        return f"Rider 18 export credits use parsed generation rates plus MPSC PSCR factors loaded for {count} {suffix}."
    return "Rider 18 export credits use parsed generation rates plus MPSC PSCR when the selected tariff has a PSCR factor."


def _tax_note() -> str:
    return (
        "Default tax is Michigan's 4.0% residential electric sales tax. "
        "Set tax rate to 0 to omit taxes from rate calculations."
    )

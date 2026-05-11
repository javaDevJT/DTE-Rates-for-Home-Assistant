from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import RATE_CARD_URL, RIDER18_CALCULATOR_URL, UPDATE_INTERVAL
from .models import ParsedRateCard
from .pdf_parser import parse_rate_card_pdf
from .pscr_parser import parse_pscr_cents_from_xlsx

_LOGGER = logging.getLogger(__name__)


class DteRateCoordinator(DataUpdateCoordinator[ParsedRateCard]):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry | None = None) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="dte_rate_card",
            config_entry=config_entry,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> ParsedRateCard:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(RATE_CARD_URL, timeout=60) as resp:
                resp.raise_for_status()
                pdf_bytes = await resp.read()
        except Exception as err:
            raise UpdateFailed(f"Failed downloading DTE rate card: {err}") from err

        pscr_bytes: bytes | None = None
        try:
            async with session.get(RIDER18_CALCULATOR_URL, timeout=60) as resp:
                resp.raise_for_status()
                pscr_bytes = await resp.read()
        except Exception as err:
            _LOGGER.warning(
                "Failed downloading DTE Rider 18 calculator; export rates will omit PSCR: %s",
                err,
            )

        try:
            parsed = await self.hass.async_add_executor_job(
                parse_rate_card_pdf,
                pdf_bytes,
                RATE_CARD_URL,
            )
        except Exception as err:
            raise UpdateFailed(f"Failed parsing DTE rate card: {err}") from err

        if pscr_bytes is None:
            return parsed

        try:
            parsed.pscr_cents = await self.hass.async_add_executor_job(
                parse_pscr_cents_from_xlsx,
                pscr_bytes,
            )
            parsed.pscr_source_url = RIDER18_CALCULATOR_URL
        except Exception as err:
            _LOGGER.warning(
                "Failed parsing DTE Rider 18 PSCR; export rates will omit PSCR: %s",
                err,
            )

        return parsed

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from custom_components.dte_rates.config_flow import DteRatesConfigFlow, DteRatesOptionsFlow
from custom_components.dte_rates.const import (
    CONF_INCLUDE_PSCR,
    CONF_NET_METERING,
    CONF_SELECTED_RATE,
    CONF_TAX_RATE,
)
from custom_components.dte_rates.models import ParsedRateCard, RatePlan


@pytest.mark.asyncio
async def test_config_flow_creates_entry_with_selected_rate(monkeypatch):
    flow = DteRatesConfigFlow()
    flow.hass = MagicMock()

    async def _refresh(self):
        self.data = ParsedRateCard(
            source_url="https://example.test/card.pdf",
            effective_date="February 6, 2025",
            rates={
                "D1.11": RatePlan(code="D1.11", name="Standard Base", periods=[]),
                "D1.13": RatePlan(code="D1.13", name="Overnight", periods=[]),
            },
            raw_text_hash="abc",
            pscr_rates={},
        )

    monkeypatch.setattr(
        "custom_components.dte_rates.coordinator.DteRateCoordinator.async_refresh",
        _refresh,
    )

    result = await flow.async_step_user(
        {
            CONF_SELECTED_RATE: "D1.13",
            CONF_NET_METERING: True,
        }
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Overnight (D1.13)"
    assert result["data"][CONF_SELECTED_RATE] == "D1.13"
    assert result["data"][CONF_NET_METERING] is True
    assert result["data"][CONF_INCLUDE_PSCR] is True
    assert result["data"][CONF_TAX_RATE] == "4.0"


@pytest.mark.asyncio
async def test_config_flow_describes_rider18_formula_status(monkeypatch):
    flow = DteRatesConfigFlow()
    flow.hass = MagicMock()

    async def _refresh(self):
        self.data = ParsedRateCard(
            source_url="https://example.test/card.pdf",
            effective_date="February 6, 2025",
            rates={
                "D1.11": RatePlan(code="D1.11", name="Standard Base", periods=[]),
                "D1.13": RatePlan(code="D1.13", name="Overnight", periods=[]),
            },
            raw_text_hash="abc",
            pscr_rates={
                "D1.11": Decimal("1.877"),
                "D1.13": Decimal("1.877"),
            },
        )

    monkeypatch.setattr(
        "custom_components.dte_rates.coordinator.DteRateCoordinator.async_refresh",
        _refresh,
    )

    result = await flow.async_step_user()

    assert result["type"] == "form"
    assert (
        result["description_placeholders"]["rider18_status"]
        == "Rider 18 export credits use parsed generation rates plus MPSC PSCR factors loaded for 2 tariffs."
    )
    assert "Set tax rate to 0" in result["description_placeholders"]["tax_note"]
    assert "Detroit residents may incur an additional 5.0%" in result["description_placeholders"]["tax_note"]


@pytest.mark.asyncio
async def test_options_flow_updates_modifiers():
    config_entry = MagicMock()
    config_entry.data = {
        CONF_SELECTED_RATE: "D1.11",
        CONF_NET_METERING: False,
        CONF_INCLUDE_PSCR: True,
        CONF_TAX_RATE: "4.0",
    }
    config_entry.options = {}
    flow = DteRatesOptionsFlow(config_entry)

    result = await flow.async_step_init(
        {
            CONF_INCLUDE_PSCR: False,
            CONF_TAX_RATE: "0",
        }
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_INCLUDE_PSCR] is False
    assert result["data"][CONF_TAX_RATE] == "0"

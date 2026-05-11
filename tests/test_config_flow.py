from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from custom_components.dte_rates.config_flow import DteRatesConfigFlow
from custom_components.dte_rates.const import CONF_NET_METERING, CONF_SELECTED_RATE
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


@pytest.mark.asyncio
async def test_config_flow_describes_rider18_loaded_status(monkeypatch):
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
            rider18_source_url="https://example.test/Rider18Calculator.xlsx",
            rider18_export_rates={
                "D1.11": {("october_through_may", "off_peak"): Decimal("10.586")},
            },
        )

    monkeypatch.setattr(
        "custom_components.dte_rates.coordinator.DteRateCoordinator.async_refresh",
        _refresh,
    )

    result = await flow.async_step_user()

    assert result["type"] == "form"
    assert result["description_placeholders"]["rider18_status"] == "Rider 18 export credits loaded for 1 rate plan."

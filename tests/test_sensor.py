from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from homeassistant.components import persistent_notification
from custom_components.dte_rates.const import CONF_NET_METERING, CONF_SELECTED_RATE
from custom_components.dte_rates.models import ParsedRateCard, PriceComponents, RatePlan, SeasonalPeriodRate, TimeWindow
from custom_components.dte_rates.sensor import (
    DteCurrentRateNameSensor,
    DteExportRateSensor,
    DteImportRateSensor,
    DteRateScheduleSensor,
)


def _coordinator_with_rate() -> SimpleNamespace:
    rate = RatePlan(
        code="D1.11",
        name="Standard Base",
        periods=[
            SeasonalPeriodRate(
                season_name="year_round",
                period_name="all_kwh",
                components=PriceComponents(
                    per_kwh={
                        "capacity_energy": Decimal("1.000"),
                        "non_capacity_energy": Decimal("2.000"),
                        "distribution_kwh": Decimal("3.000"),
                    }
                ),
                window=TimeWindow(label="all_kwh"),
            )
        ],
    )
    return SimpleNamespace(
        data=ParsedRateCard(
            source_url="https://example.test/card.pdf",
            effective_date="February 6, 2025",
            rates={"D1.11": rate},
            raw_text_hash="hash",
        )
    )


def test_import_sensor_returns_total_rate(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.sensor.dt_util.now", lambda: datetime(2026, 3, 1, 12, 0))

    coordinator = _coordinator_with_rate()
    entry = SimpleNamespace(entry_id="entry_1", data={CONF_SELECTED_RATE: "D1.11", CONF_NET_METERING: False})

    sensor = DteImportRateSensor(coordinator, entry)
    assert sensor.native_value == 0.06
    assert sensor.native_unit_of_measurement == "USD/kWh"
    assert sensor.extra_state_attributes["selected_rate_available"] is True
    assert sensor.extra_state_attributes["current_rate_name"] == "All kWh"
    assert sensor.extra_state_attributes["next_rate_change"] is None


def test_export_sensor_uses_generation_only_without_net_metering(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.sensor.dt_util.now", lambda: datetime(2026, 3, 1, 12, 0))

    coordinator = _coordinator_with_rate()
    entry = SimpleNamespace(entry_id="entry_2", data={CONF_SELECTED_RATE: "D1.11", CONF_NET_METERING: False})

    sensor = DteExportRateSensor(coordinator, entry)
    assert sensor.native_value == 0.03
    assert sensor.extra_state_attributes["next_rate_value"] is None


def test_sensor_warns_when_selected_rate_disappears(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.sensor.dt_util.now", lambda: datetime(2026, 3, 1, 12, 0))

    coordinator = _coordinator_with_rate()
    entry = SimpleNamespace(entry_id="entry_3", data={CONF_SELECTED_RATE: "D9", CONF_NET_METERING: False})

    sensor = DteImportRateSensor(coordinator, entry)
    assert sensor.native_value is None
    assert sensor.extra_state_attributes["selected_rate_available"] is False
    assert "no longer present" in sensor.extra_state_attributes["warning"]


def test_attributes_include_next_rate_metadata(monkeypatch):
    now = datetime(2026, 3, 1, 12, 0)
    monkeypatch.setattr("custom_components.dte_rates.sensor.dt_util.now", lambda: now)

    coordinator = _coordinator_with_rate()
    next_period = SeasonalPeriodRate(
        season_name="june_through_september",
        period_name="peak",
        components=PriceComponents(per_kwh={"capacity_energy": Decimal("2.500"), "non_capacity_energy": Decimal("1.500")}),
        window=TimeWindow(label="peak"),
    )
    monkeypatch.setattr(
        "custom_components.dte_rates.sensor.get_next_rate_change",
        lambda rate, dt: (datetime(2026, 3, 1, 15, 0), next_period),
    )

    entry = SimpleNamespace(entry_id="entry_6", data={CONF_SELECTED_RATE: "D1.11", CONF_NET_METERING: False})
    sensor = DteExportRateSensor(coordinator, entry)
    attrs = sensor.extra_state_attributes

    assert attrs["next_rate_change"] == "2026-03-01T15:00:00"
    assert attrs["next_rate_name"] == "Summer On-Peak"
    assert attrs["next_rate_value"] == 0.04


def test_current_rate_name_sensor(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.sensor.dt_util.now", lambda: datetime(2026, 3, 1, 12, 0))
    coordinator = _coordinator_with_rate()
    entry = SimpleNamespace(entry_id="entry_7", data={CONF_SELECTED_RATE: "D1.11", CONF_NET_METERING: False})

    sensor = DteCurrentRateNameSensor(coordinator, entry)
    assert sensor.native_value == "All kWh"
    assert sensor.native_unit_of_measurement is None


def test_schedule_sensor_exposes_full_schedule(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.sensor.dt_util.now", lambda: datetime(2026, 3, 1, 12, 0))
    coordinator = _coordinator_with_rate()
    entry = SimpleNamespace(entry_id="entry_8", data={CONF_SELECTED_RATE: "D1.11", CONF_NET_METERING: False})

    sensor = DteRateScheduleSensor(coordinator, entry)
    attrs = sensor.extra_state_attributes

    assert sensor.native_value == "D1.11 (1 periods)"
    assert len(attrs["schedule_by_season"]) == 1
    assert "Import $0.0600/kWh" in attrs["schedule_text"]
    assert "Export $0.0300/kWh" in attrs["schedule_text"]
    assert attrs["schedule_by_season"][0]["export_usd_per_kwh"] == 0.03
    assert attrs["next_rate_value"] is None


def test_schedule_sensor_next_rate_value_defaults_to_import(monkeypatch):
    now = datetime(2026, 3, 1, 12, 0)
    monkeypatch.setattr("custom_components.dte_rates.sensor.dt_util.now", lambda: now)
    coordinator = _coordinator_with_rate()
    next_period = SeasonalPeriodRate(
        season_name="june_through_september",
        period_name="peak",
        components=PriceComponents(
            per_kwh={
                "capacity_energy": Decimal("2.500"),
                "non_capacity_energy": Decimal("1.500"),
                "distribution_kwh": Decimal("3.000"),
            }
        ),
        window=TimeWindow(label="peak"),
    )
    monkeypatch.setattr(
        "custom_components.dte_rates.sensor.get_next_rate_change",
        lambda rate, dt: (datetime(2026, 3, 1, 15, 0), next_period),
    )

    entry = SimpleNamespace(entry_id="entry_10", data={CONF_SELECTED_RATE: "D1.11", CONF_NET_METERING: False})
    sensor = DteRateScheduleSensor(coordinator, entry)
    attrs = sensor.extra_state_attributes

    assert attrs["next_rate_value"] == 0.07


def test_entities_publish_service_device_info(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.sensor.dt_util.now", lambda: datetime(2026, 3, 1, 12, 0))
    coordinator = _coordinator_with_rate()
    entry = SimpleNamespace(entry_id="entry_9", data={CONF_SELECTED_RATE: "D1.11", CONF_NET_METERING: False})

    sensor = DteImportRateSensor(coordinator, entry)
    info = sensor.device_info
    assert ("dte_rates", "entry_9") in info["identifiers"]
    assert info["entry_type"] == "service"


def test_missing_rate_creates_persistent_notification(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.sensor.dt_util.now", lambda: datetime(2026, 3, 1, 12, 0))
    create_mock = MagicMock()
    dismiss_mock = MagicMock()
    monkeypatch.setattr(persistent_notification, "async_create", create_mock)
    monkeypatch.setattr(persistent_notification, "async_dismiss", dismiss_mock)

    coordinator = _coordinator_with_rate()
    entry = SimpleNamespace(entry_id="entry_4", title="My DTE Plan", data={CONF_SELECTED_RATE: "D9", CONF_NET_METERING: False})
    sensor = DteImportRateSensor(coordinator, entry)
    sensor.hass = SimpleNamespace()

    _ = sensor.extra_state_attributes

    create_mock.assert_called_once()
    dismiss_mock.assert_not_called()


def test_available_rate_dismisses_existing_notification(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.sensor.dt_util.now", lambda: datetime(2026, 3, 1, 12, 0))
    create_mock = MagicMock()
    dismiss_mock = MagicMock()
    monkeypatch.setattr(persistent_notification, "async_create", create_mock)
    monkeypatch.setattr(persistent_notification, "async_dismiss", dismiss_mock)

    coordinator = _coordinator_with_rate()
    entry = SimpleNamespace(entry_id="entry_5", title="My DTE Plan", data={CONF_SELECTED_RATE: "D1.11", CONF_NET_METERING: False})
    sensor = DteImportRateSensor(coordinator, entry)
    sensor.hass = SimpleNamespace()

    _ = sensor.extra_state_attributes

    create_mock.assert_not_called()
    dismiss_mock.assert_called_once()

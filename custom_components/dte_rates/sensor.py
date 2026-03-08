from __future__ import annotations

from collections import defaultdict

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_CARD_EFFECTIVE_DATE,
    ATTR_COMPONENTS,
    ATTR_MONTHLY_COMPONENTS,
    ATTR_PERIOD,
    ATTR_CURRENT_RATE_NAME,
    ATTR_NEXT_RATE_CHANGE,
    ATTR_NEXT_RATE_NAME,
    ATTR_NEXT_RATE_VALUE,
    ATTR_RATE_CODE,
    ATTR_RATE_NAME,
    ATTR_SCHEDULE_BY_SEASON,
    ATTR_SCHEDULE_TEXT,
    ATTR_SEASON,
    ATTR_SELECTED_RATE_AVAILABLE,
    ATTR_SOURCE_URL,
    ATTR_WARNING,
    CONF_NET_METERING,
    CONF_SELECTED_RATE,
    DOMAIN,
)
from .models import RatePlan, SeasonalPeriodRate
from .rate_calculator import (
    current_export_rate_cents,
    current_import_rate_cents,
    get_active_period,
    get_next_rate_change,
    period_display_name,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        DteImportRateSensor(coordinator, entry),
        DteExportRateSensor(coordinator, entry),
        DteCurrentRateNameSensor(coordinator, entry),
        DteRateScheduleSensor(coordinator, entry),
    ])


class _DteBaseRateSensor(CoordinatorEntity, SensorEntity):
    _attr_native_unit_of_measurement = "USD/kWh"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._notification_id = f"dte_rates_missing_rate_{entry.entry_id}"

    def _selected_rate(self) -> RatePlan | None:
        selected = self._entry.data[CONF_SELECTED_RATE]
        return self.coordinator.data.rates.get(selected)

    @property
    def device_info(self) -> dict:
        rate = self._selected_rate()
        rate_name = rate.name if rate else self._entry.data.get(CONF_SELECTED_RATE, "DTE Rate")
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": rate_name,
            "manufacturer": "DTE Energy",
            "model": "Residential Electric Rate",
            "entry_type": DeviceEntryType.SERVICE,
            "configuration_url": "https://www.dteenergy.com/rateoptions",
        }

    def _active_period(self) -> SeasonalPeriodRate | None:
        rate = self._selected_rate()
        if rate is None:
            return None
        return get_active_period(rate, dt_util.now())

    def _warning(self) -> str | None:
        selected = self._entry.data[CONF_SELECTED_RATE]
        if selected not in self.coordinator.data.rates:
            return f"Selected rate '{selected}' is no longer present in the latest DTE rate card."
        return None

    def _base_attributes(self) -> dict:
        warning = self._warning()
        self._sync_missing_rate_notification(warning)
        attrs = {
            ATTR_SELECTED_RATE_AVAILABLE: warning is None,
            ATTR_WARNING: warning,
            ATTR_SOURCE_URL: self.coordinator.data.source_url,
            ATTR_CARD_EFFECTIVE_DATE: self.coordinator.data.effective_date,
        }

        rate = self._selected_rate()
        period = self._active_period()
        if rate is None or period is None:
            return attrs

        next_change = get_next_rate_change(rate, dt_util.now())
        next_change_at = next_change[0].isoformat() if next_change else None
        next_period = next_change[1] if next_change else None

        attrs.update(
            {
                ATTR_RATE_CODE: rate.code,
                ATTR_RATE_NAME: rate.name,
                ATTR_SEASON: period.season_name,
                ATTR_PERIOD: period.period_name,
                ATTR_CURRENT_RATE_NAME: period_display_name(period),
                ATTR_NEXT_RATE_CHANGE: next_change_at,
                ATTR_NEXT_RATE_NAME: period_display_name(next_period) if next_period else None,
                ATTR_NEXT_RATE_VALUE: self._period_value_usd(next_period) if next_period else None,
                ATTR_COMPONENTS: {k: float(v) for k, v in period.components.per_kwh.items()},
                ATTR_MONTHLY_COMPONENTS: {k: float(v) for k, v in period.components.monthly.items()},
            }
        )
        return attrs

    def _period_value_usd(self, period: SeasonalPeriodRate | None) -> float | None:
        raise NotImplementedError

    @staticmethod
    def _format_hour(hour: int) -> str:
        suffix = "AM" if hour < 12 else "PM"
        h12 = hour % 12
        if h12 == 0:
            h12 = 12
        return f"{h12}:00 {suffix}"

    def _window_summary(self, period: SeasonalPeriodRate) -> str:
        window = period.window
        if not window.hour_ranges:
            return "All day"
        chunks = []
        for start, end in window.hour_ranges:
            chunks.append(f"{self._format_hour(start)}-{self._format_hour(end)}")
        return ", ".join(chunks)

    def _schedule_rows(self, rate: RatePlan) -> list[dict]:
        rows: list[dict] = []
        for period in sorted(rate.periods, key=lambda p: (p.season_name, p.period_name)):
            rows.append(
                {
                    "season": period.season_name,
                    "period": period.period_name,
                    "name": period_display_name(period),
                    "time_window": self._window_summary(period),
                    "import_usd_per_kwh": round(float(current_import_rate_cents(period) / 100), 6),
                    "export_usd_per_kwh": round(float(self._period_value_usd(period) or 0.0), 6),
                }
            )
        return rows

    def _schedule_text(self, rate: RatePlan) -> str:
        grouped: dict[str, list[str]] = defaultdict(list)
        for row in self._schedule_rows(rate):
            grouped[row["season"]].append(
                (
                    f"{row['name']}: {row['time_window']} | "
                    f"Import ${row['import_usd_per_kwh']:.4f}/kWh | "
                    f"Export ${row['export_usd_per_kwh']:.4f}/kWh"
                )
            )

        lines: list[str] = []
        for season in sorted(grouped):
            lines.append(f"[{season}]")
            lines.extend(grouped[season])
        return "\n".join(lines)

    def _sync_missing_rate_notification(self, warning: str | None) -> None:
        if getattr(self, "hass", None) is None:
            return

        if warning:
            persistent_notification.async_create(
                self.hass,
                (
                    f"{warning}\n\n"
                    f"Integration entry: {self._entry.title if hasattr(self._entry, 'title') else self._entry.entry_id}"
                ),
                title="DTE Rates Warning",
                notification_id=self._notification_id,
            )
            return

        persistent_notification.async_dismiss(
            self.hass,
            self._notification_id,
        )


class DteImportRateSensor(_DteBaseRateSensor):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_import_rate"
        self._attr_name = "DTE Import Rate"
        self._attr_icon = "mdi:transmission-tower-import"

    @property
    def native_value(self) -> float | None:
        period = self._active_period()
        if period is None:
            return None
        return self._period_value_usd(period)

    @property
    def extra_state_attributes(self) -> dict:
        return self._base_attributes()

    def _period_value_usd(self, period: SeasonalPeriodRate | None) -> float | None:
        if period is None:
            return None
        return float(current_import_rate_cents(period) / 100)


class DteExportRateSensor(_DteBaseRateSensor):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_export_rate"
        self._attr_name = "DTE Export Rate"
        self._attr_icon = "mdi:transmission-tower-export"

    @property
    def native_value(self) -> float | None:
        period = self._active_period()
        if period is None:
            return None
        return self._period_value_usd(period)

    @property
    def extra_state_attributes(self) -> dict:
        attrs = self._base_attributes()
        attrs[CONF_NET_METERING] = self._entry.data.get(CONF_NET_METERING, False)
        return attrs

    def _period_value_usd(self, period: SeasonalPeriodRate | None) -> float | None:
        if period is None:
            return None
        cents = current_export_rate_cents(period, self._entry.data.get(CONF_NET_METERING, False))
        return float(cents / 100)


class DteCurrentRateNameSensor(_DteBaseRateSensor):
    _attr_native_unit_of_measurement = None
    _attr_device_class = None
    _attr_state_class = None

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_rate_name"
        self._attr_name = "DTE Current Rate Name"
        self._attr_icon = "mdi:tag-text-outline"

    @property
    def native_value(self) -> str | None:
        period = self._active_period()
        if period is None:
            return None
        return period_display_name(period)

    @property
    def extra_state_attributes(self) -> dict:
        return self._base_attributes()

    def _period_value_usd(self, period: SeasonalPeriodRate | None) -> float | None:
        if period is None:
            return None
        return float(current_import_rate_cents(period) / 100)


class DteRateScheduleSensor(_DteBaseRateSensor):
    _attr_native_unit_of_measurement = None
    _attr_device_class = None
    _attr_state_class = None

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_rate_schedule"
        self._attr_name = "DTE Rate Schedule"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> str | None:
        rate = self._selected_rate()
        if rate is None:
            return None
        return f"{rate.code} ({len(rate.periods)} periods)"

    @property
    def extra_state_attributes(self) -> dict:
        attrs = self._base_attributes()
        rate = self._selected_rate()
        if rate is None:
            return attrs
        rows = self._schedule_rows(rate)
        attrs[ATTR_SCHEDULE_BY_SEASON] = rows
        attrs[ATTR_SCHEDULE_TEXT] = self._schedule_text_from_rows(rows)
        return attrs

    def _schedule_rows(self, rate: RatePlan) -> list[dict]:
        rows: list[dict] = []
        net_metering = self._entry.data.get(CONF_NET_METERING, False)
        for period in sorted(rate.periods, key=lambda p: (p.season_name, p.period_name)):
            rows.append(
                {
                    "season": period.season_name,
                    "period": period.period_name,
                    "name": period_display_name(period),
                    "time_window": self._window_summary(period),
                    "import_usd_per_kwh": round(float(current_import_rate_cents(period) / 100), 6),
                    "export_usd_per_kwh": round(float(current_export_rate_cents(period, net_metering) / 100), 6),
                }
            )
        return rows

    def _schedule_text_from_rows(self, rows: list[dict]) -> str:
        grouped: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            grouped[row["season"]].append(
                (
                    f"{row['name']}: {row['time_window']} | "
                    f"Import ${row['import_usd_per_kwh']:.4f}/kWh | "
                    f"Export ${row['export_usd_per_kwh']:.4f}/kWh"
                )
            )

        lines: list[str] = []
        for season in sorted(grouped):
            lines.append(f"[{season}]")
            lines.extend(grouped[season])
        return "\n".join(lines)

    def _period_value_usd(self, period: SeasonalPeriodRate | None) -> float | None:
        if period is None:
            return None
        return float(current_import_rate_cents(period) / 100)

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from custom_components.dte_rates.models import PriceComponents, RatePlan, SeasonalPeriodRate, TimeWindow
from custom_components.dte_rates.rate_calculator import (
    current_export_rate_cents,
    current_import_rate_cents,
    get_active_period,
    get_next_rate_change,
    period_display_name,
)


def _rate_plan() -> RatePlan:
    return RatePlan(
        code="D1.11",
        name="Time of Day 3 p.m. - 7 p.m. Standard Base Rate",
        periods=[
            SeasonalPeriodRate(
                season_name="june_through_september",
                period_name="peak",
                components=PriceComponents(
                    per_kwh={
                        "capacity_energy": Decimal("5.360"),
                        "non_capacity_energy": Decimal("9.047"),
                        "distribution_kwh": Decimal("9.726"),
                    }
                ),
                window=TimeWindow(label="peak", weekdays_only=True, hour_ranges=[(15, 19)], months={6, 7, 8, 9}),
            ),
            SeasonalPeriodRate(
                season_name="june_through_september",
                period_name="off_peak",
                components=PriceComponents(
                    per_kwh={
                        "capacity_energy": Decimal("3.240"),
                        "non_capacity_energy": Decimal("5.469"),
                        "distribution_kwh": Decimal("9.726"),
                    }
                ),
                window=TimeWindow(label="off_peak", months={6, 7, 8, 9}),
            ),
        ],
    )


def test_get_active_period_for_weekday_peak_hours():
    rate = _rate_plan()
    active = get_active_period(rate, datetime(2026, 6, 1, 16, 30))
    assert active is not None
    assert active.period_name == "peak"


def test_get_active_period_for_weekend_returns_off_peak():
    rate = _rate_plan()
    active = get_active_period(rate, datetime(2026, 6, 6, 16, 30))
    assert active is not None
    assert active.period_name == "off_peak"


def test_import_is_total_of_all_per_kwh_components():
    rate = _rate_plan()
    active = get_active_period(rate, datetime(2026, 6, 1, 16, 30))
    assert active is not None
    assert current_import_rate_cents(active) == Decimal("24.133")


def test_export_without_net_metering_only_generation():
    rate = _rate_plan()
    active = get_active_period(rate, datetime(2026, 6, 1, 16, 30))
    assert active is not None
    assert current_export_rate_cents(active, net_metering=False) == Decimal("14.407")


def test_export_with_net_metering_uses_total():
    rate = _rate_plan()
    active = get_active_period(rate, datetime(2026, 6, 1, 16, 30))
    assert active is not None
    assert current_export_rate_cents(active, net_metering=True) == Decimal("24.133")


def test_multiple_hour_ranges_supported_for_same_period():
    rate = RatePlan(
        code="D1.8",
        name="Dynamic",
        periods=[
            SeasonalPeriodRate(
                season_name="year_round",
                period_name="mid_peak",
                components=PriceComponents(per_kwh={"x": Decimal("1")}),
                window=TimeWindow(label="mid_peak", weekdays_only=True, hour_ranges=[(7, 15), (19, 23)]),
            ),
            SeasonalPeriodRate(
                season_name="year_round",
                period_name="off_peak",
                components=PriceComponents(per_kwh={"x": Decimal("2")}),
                window=TimeWindow(label="off_peak"),
            ),
        ],
    )

    assert get_active_period(rate, datetime(2026, 6, 1, 8, 0)).period_name == "mid_peak"
    assert get_active_period(rate, datetime(2026, 6, 1, 20, 0)).period_name == "mid_peak"
    assert get_active_period(rate, datetime(2026, 6, 1, 16, 0)).period_name == "off_peak"


def test_next_rate_change_detected():
    rate = _rate_plan()
    result = get_next_rate_change(rate, datetime(2026, 6, 1, 16, 0))
    assert result is not None
    when, next_period = result
    assert when.isoformat() == "2026-06-01T19:00:00"
    assert next_period.period_name == "off_peak"


def test_next_rate_change_alignment_does_not_drift_minutes():
    rate = _rate_plan()
    result = get_next_rate_change(rate, datetime(2026, 6, 1, 18, 56))
    assert result is not None
    when, next_period = result
    assert when.isoformat() == "2026-06-01T19:00:00"
    assert next_period.period_name == "off_peak"


def test_period_display_name():
    period = SeasonalPeriodRate(
        season_name="june_through_september",
        period_name="peak",
        components=PriceComponents(per_kwh={"x": Decimal("1.0")}),
        window=TimeWindow(label="peak"),
    )
    assert period_display_name(period) == "Summer On-Peak"

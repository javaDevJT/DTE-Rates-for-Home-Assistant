from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from .models import RatePlan, SeasonalPeriodRate


GENERATION_COMPONENT_MARKERS = ("capacity_energy", "non_capacity_energy")


def _is_hour_in_range(start_hour: int, end_hour: int, hour: int) -> bool:
    if start_hour <= end_hour:
        return start_hour <= hour < end_hour
    return hour >= start_hour or hour < end_hour


def _is_hour_match(period: SeasonalPeriodRate, hour: int) -> bool:
    ranges = period.window.hour_ranges
    if not ranges:
        return True
    return any(_is_hour_in_range(start, end, hour) for start, end in ranges)


def _coverage_hours(period: SeasonalPeriodRate) -> int:
    if not period.window.hour_ranges:
        return 24
    total = 0
    for start, end in period.window.hour_ranges:
        total += (end - start) % 24
    return total


def _period_sort_key(period: SeasonalPeriodRate) -> tuple[int, int, int, str]:
    has_hours = 0 if period.window.hour_ranges else 1
    weekday_scope = 0 if period.window.weekdays_only or period.window.weekends_only else 1
    return (has_hours, weekday_scope, _coverage_hours(period), period.period_name)


def get_active_period(rate: RatePlan, now: datetime) -> SeasonalPeriodRate | None:
    weekday = now.weekday() < 5
    hour = now.hour
    month = now.month

    candidates = sorted(rate.periods, key=_period_sort_key)
    for period in candidates:
        window = period.window

        if window.months and month not in window.months:
            continue
        if window.weekdays_only and not weekday:
            continue
        if window.weekends_only and weekday:
            continue
        if not weekday and window.weekends_all_day:
            return period
        if not _is_hour_match(period, hour):
            continue
        return period

    return None


def current_import_rate_cents(period: SeasonalPeriodRate) -> Decimal:
    return period.components.per_kwh_total


def current_export_rate_cents(period: SeasonalPeriodRate, net_metering: bool) -> Decimal:
    if net_metering:
        return period.components.per_kwh_total

    generation_only = Decimal("0")
    for key, value in period.components.per_kwh.items():
        if any(marker in key for marker in GENERATION_COMPONENT_MARKERS):
            generation_only += value
    return generation_only


def period_display_name(period: SeasonalPeriodRate) -> str:
    season_label = {
        "june_through_september": "Summer",
        "june_through_october": "Summer",
        "october_through_may": "Winter",
        "november_through_may": "Winter",
        "year_round": "Year-round",
    }.get(period.season_name, period.season_name.replace("_", " ").title())

    period_label = {
        "peak": "On-Peak",
        "off_peak": "Off-Peak",
        "super_off_peak": "Super Off-Peak",
        "mid_peak": "Mid-Peak",
        "critical_peak": "Critical Peak",
        "all_kwh": "All kWh",
    }.get(period.period_name, period.period_name.replace("_", " ").title())

    if season_label == "Year-round":
        return period_label
    return f"{season_label} {period_label}"


def get_next_rate_change(
    rate: RatePlan,
    now: datetime,
    *,
    step_minutes: int = 15,
    horizon_days: int = 400,
) -> tuple[datetime, SeasonalPeriodRate] | None:
    current = get_active_period(rate, now)
    if current is None:
        return None

    current_key = (
        current.season_name,
        current.period_name,
        current.components.per_kwh_total,
    )
    start = _align_to_next_step(now, step_minutes)
    steps = int((horizon_days * 24 * 60) / step_minutes)

    probe = start
    for _ in range(steps):
        candidate = get_active_period(rate, probe)
        if candidate is not None:
            candidate_key = (
                candidate.season_name,
                candidate.period_name,
                candidate.components.per_kwh_total,
            )
            if candidate_key != current_key:
                return probe, candidate
        probe += timedelta(minutes=step_minutes)

    return None


def _align_to_next_step(now: datetime, step_minutes: int) -> datetime:
    base = now.replace(second=0, microsecond=0)
    remainder = base.minute % step_minutes
    if remainder == 0:
        return base + timedelta(minutes=step_minutes)
    return base + timedelta(minutes=(step_minutes - remainder))

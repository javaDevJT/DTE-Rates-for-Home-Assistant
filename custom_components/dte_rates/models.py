from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(slots=True)
class PriceComponents:
    per_kwh: dict[str, Decimal] = field(default_factory=dict)
    monthly: dict[str, Decimal] = field(default_factory=dict)

    @property
    def per_kwh_total(self) -> Decimal:
        return sum(self.per_kwh.values(), Decimal("0"))

    @property
    def monthly_total(self) -> Decimal:
        return sum(self.monthly.values(), Decimal("0"))


@dataclass(slots=True)
class TimeWindow:
    label: str
    weekdays_only: bool = False
    weekends_only: bool = False
    weekends_all_day: bool = False
    hour_ranges: list[tuple[int, int]] = field(default_factory=list)
    months: set[int] = field(default_factory=lambda: set(range(1, 13)))


@dataclass(slots=True)
class SeasonalPeriodRate:
    season_name: str
    period_name: str
    components: PriceComponents
    window: TimeWindow


@dataclass(slots=True)
class RatePlan:
    code: str
    name: str
    periods: list[SeasonalPeriodRate]
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ParsedRateCard:
    source_url: str
    effective_date: str | None
    rates: dict[str, RatePlan]
    raw_text_hash: str

from __future__ import annotations

import hashlib
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from pypdf import PdfReader

from .models import ParsedRateCard, PriceComponents, RatePlan, SeasonalPeriodRate, TimeWindow


RATE_HEADER_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<code>D[\d.]+)\)$", re.MULTILINE)
SEASON_RE = re.compile(
    r"^(June through September|June through October|October through May|November through May|Year-round)$",
    re.IGNORECASE,
)
PERIOD_LINE_RE = re.compile(
    r"^(All\s+.+?\s+kWh|First\s+\d+\s+kWh\s+per\s+day|Additional\s+kWh)",
    re.IGNORECASE,
)
VALUE_RE = re.compile(
    r"^(?P<label>.+?)\s*\.{2,}\s*(?P<value>\(?\$?\d+\.\d+\)?)\s*(?P<unit>¢\s*per\s*kWh|\$\s*per\s*month|\$\s*per\s*day)$",
    re.IGNORECASE,
)
INLINE_CENTS_RE = re.compile(r"(?P<value>\d+\.\d+)\s*¢\s*per\s*kWh", re.IGNORECASE)
TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)", re.IGNORECASE)


@dataclass(slots=True)
class _WindowSpec:
    weekdays_only: bool = False
    weekends_only: bool = False
    weekends_all_day: bool = False
    hour_ranges: list[tuple[int, int]] = field(default_factory=list)


def _to_decimal(num: str) -> Decimal:
    cleaned = num.replace("$", "").replace("(", "-").replace(")", "")
    return Decimal(cleaned)


def _normalize_key(text: str) -> str:
    key = text.lower().strip()
    key = re.sub(r"[^a-z0-9]+", "_", key)
    return re.sub(r"_+", "_", key).strip("_")


def _months_for(season: str) -> set[int]:
    mapping = {
        "june_through_september": {6, 7, 8, 9},
        "june_through_october": {6, 7, 8, 9, 10},
        "october_through_may": {10, 11, 12, 1, 2, 3, 4, 5},
        "november_through_may": {11, 12, 1, 2, 3, 4, 5},
        "year_round": set(range(1, 13)),
    }
    return mapping.get(season, set(range(1, 13)))


def _canonical_period_name(raw: str) -> str:
    lower = raw.lower().strip().replace("-", " ")
    if lower.startswith("first"):
        return "first_block"
    if lower.startswith("additional"):
        return "additional_block"

    cleaned = re.sub(r"^all\s+", "", lower)
    cleaned = re.sub(r"\s+kwh$", "", cleaned).strip()
    normalized = _normalize_key(cleaned)
    if normalized:
        return normalized
    return "all_kwh"


def _period_from_component_label(label: str) -> str | None:
    lower = label.lower()
    if lower == "distribution_kwh":
        return "all_kwh"
    m = re.match(r"distribution_(.+)_kwh$", lower)
    if m:
        return _canonical_period_name(m.group(1))
    return None


def _to_hour(hour_txt: str, minute_txt: str | None, meridiem_txt: str) -> int:
    hour = int(hour_txt)
    minute = int(minute_txt or "0")
    meridiem = meridiem_txt.lower().replace(".", "")

    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0

    if minute >= 30:
        hour = (hour + 1) % 24
    return hour


def _extract_hour_ranges(text: str) -> list[tuple[int, int]]:
    tokens = [
        _to_hour(m.group(1), m.group(2), m.group(3))
        for m in TIME_RE.finditer(text)
    ]

    ranges: list[tuple[int, int]] = []
    for idx in range(0, len(tokens) - 1, 2):
        ranges.append((tokens[idx], tokens[idx + 1]))
    return ranges


def _period_hint_from_line(line: str) -> str | None:
    lower = line.lower().replace("-", " ")
    hours_label = re.match(r"^\s*([a-z0-9 ]+?)\s+hours?:", lower)
    if hours_label:
        return _canonical_period_name(hours_label.group(1))

    hints = [
        "critical peak",
        "super off peak",
        "mid peak",
        "off peak",
        "on peak",
        "peak",
    ]
    for hint in hints:
        if hint in lower:
            if hint == "on peak":
                return "peak"
            return _canonical_period_name(hint)

    m = re.search(r"all\s+(.+?)\s+kwh", lower)
    if m:
        return _canonical_period_name(m.group(1))
    return None


def _line_has_weekday_scope(line: str) -> bool:
    lower = line.lower()
    return "monday" in lower and "friday" in lower or "weekday" in lower


def _line_has_weekend_scope(line: str) -> bool:
    lower = line.lower()
    return "saturday" in lower or "sunday" in lower or "weekend" in lower


def _extract_window_specs(section: str) -> dict[str, _WindowSpec]:
    specs: dict[str, _WindowSpec] = {}
    lines = [re.sub(r"\s+", " ", line.strip()) for line in section.splitlines() if line.strip()]

    current_hint: str | None = None
    for line in lines:
        lower = line.lower()
        hint = _period_hint_from_line(line)
        if hint is not None:
            current_hint = hint

        target = hint
        if target is None and "from" in lower and ("a.m" in lower or "p.m" in lower):
            target = current_hint
        if target is None:
            continue

        if target not in specs:
            specs[target] = _WindowSpec()
        spec = specs[target]

        ranges = _extract_hour_ranges(line)
        for hour_range in ranges:
            if hour_range not in spec.hour_ranges:
                spec.hour_ranges.append(hour_range)

        has_weekday = _line_has_weekday_scope(line)
        has_weekend = _line_has_weekend_scope(line)

        if has_weekday and not has_weekend:
            spec.weekdays_only = True
        if has_weekend and not has_weekday and "all day" in lower:
            spec.weekends_all_day = True
            if not ranges:
                spec.weekends_only = True
        if has_weekday and has_weekend:
            spec.weekdays_only = False
            spec.weekends_only = False

        if "all other" in lower:
            spec.hour_ranges = []

    return specs


def parse_rate_card_pdf(pdf_bytes: bytes, source_url: str) -> ParsedRateCard:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized = (
        text.replace("\u2013", "-")
        .replace("\u2011", "-")
        .replace("\xa0", " ")
        .replace("™", "")
    )
    raw_text_hash = hashlib.sha256(normalized.encode()).hexdigest()

    effective_date = None
    effective_match = re.search(r"in effect as of ([A-Za-z]+\s+\d{1,2},\s+\d{4})", normalized)
    if effective_match:
        effective_date = effective_match.group(1)

    matches = list(RATE_HEADER_RE.finditer(normalized))
    rates: dict[str, RatePlan] = {}

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(normalized)
        section = normalized[start:end]

        name = match.group("name").strip()
        code = match.group("code").strip()

        periods, notes = _parse_rate_section(section)
        if periods:
            rates[code] = RatePlan(code=code, name=name, periods=periods, notes=notes)

    return ParsedRateCard(
        source_url=source_url,
        effective_date=effective_date,
        rates=rates,
        raw_text_hash=raw_text_hash,
    )


def _parse_rate_section(section: str) -> tuple[list[SeasonalPeriodRate], list[str]]:
    lines = [line.strip() for line in section.splitlines() if line.strip()]

    season = "year_round"
    current_period = "all_kwh"
    per_kwh: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(dict)
    monthly_by_season: dict[str, dict[str, Decimal]] = defaultdict(dict)
    notes: list[str] = []
    window_specs = _extract_window_specs(section)

    for raw_line in lines:
        line = re.sub(r"\s+", " ", raw_line)

        season_match = SEASON_RE.match(line)
        if season_match:
            season = _normalize_key(season_match.group(1))
            continue

        lower = line.lower()
        if lower.startswith("delivery charges"):
            current_period = "all_kwh"
            continue

        period_match = PERIOD_LINE_RE.match(line)
        if period_match:
            current_period = _canonical_period_name(period_match.group(1))

        value_match = VALUE_RE.match(line)
        if not value_match:
            if any(token in lower for token in ("no longer accepting", "enrollment is now closed", "fully subscribed")):
                notes.append(line)
            inline_match = INLINE_CENTS_RE.search(line)
            if inline_match and "all critical-peak kwh" in lower:
                key = (season, "critical_peak")
                per_kwh[key][_normalize_key("critical_peak_event_energy")] = Decimal(inline_match.group("value"))
            continue

        component_label = _normalize_key(value_match.group("label"))
        value = _to_decimal(value_match.group("value"))
        unit = value_match.group("unit").lower().replace(" ", "")

        if "¢perkwh" in unit:
            period_name = _period_from_component_label(component_label) or current_period
            key = (season, period_name)
            per_kwh[key][component_label] = value
        else:
            monthly_by_season[season][component_label] = value

    periods: list[SeasonalPeriodRate] = []
    for (period_season, period_name), kwh_components in per_kwh.items():
        monthly_components = dict(monthly_by_season.get(period_season, {}))
        window = _window_for_period(period_name, period_season, window_specs)
        periods.append(
            SeasonalPeriodRate(
                season_name=period_season,
                period_name=period_name,
                components=PriceComponents(per_kwh=dict(kwh_components), monthly=monthly_components),
                window=window,
            )
        )

    return periods, notes


def _window_for_period(period_name: str, season: str, specs: dict[str, _WindowSpec]) -> TimeWindow:
    spec = specs.get(period_name)
    if spec is None:
        return TimeWindow(label=period_name, months=_months_for(season))

    return TimeWindow(
        label=period_name,
        weekdays_only=spec.weekdays_only,
        weekends_only=spec.weekends_only,
        weekends_all_day=spec.weekends_all_day,
        hour_ranges=list(spec.hour_ranges),
        months=_months_for(season),
    )

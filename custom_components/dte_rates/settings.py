from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .const import (
    CONF_INCLUDE_PSCR,
    CONF_TAX_RATE,
    DEFAULT_INCLUDE_PSCR,
    DEFAULT_TAX_RATE_PERCENT,
)


def parse_tax_rate_percent(value: Any) -> Decimal:
    if value is None or value == "":
        value = DEFAULT_TAX_RATE_PERCENT

    raw = str(value).strip()
    if raw.endswith("%"):
        raw = raw[:-1].strip()

    try:
        tax_rate = Decimal(raw)
    except (InvalidOperation, ValueError) as err:
        raise ValueError("Tax rate must be a non-negative percentage.") from err

    if tax_rate < 0:
        raise ValueError("Tax rate must be a non-negative percentage.")
    return tax_rate


def normalize_tax_rate_percent(value: Any) -> str:
    return str(parse_tax_rate_percent(value))


def entry_include_pscr(entry) -> bool:
    return _as_bool(_entry_setting(entry, CONF_INCLUDE_PSCR, DEFAULT_INCLUDE_PSCR))


def entry_tax_rate_percent(entry) -> Decimal:
    return parse_tax_rate_percent(_entry_setting(entry, CONF_TAX_RATE, DEFAULT_TAX_RATE_PERCENT))


def _entry_setting(entry, key: str, default: Any) -> Any:
    options = getattr(entry, "options", None) or {}
    if key in options:
        return options[key]
    data = getattr(entry, "data", None) or {}
    return data.get(key, default)


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)

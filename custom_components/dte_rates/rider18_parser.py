from __future__ import annotations

from decimal import Decimal, InvalidOperation
import posixpath
import re
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from io import BytesIO


_CELL_RE = re.compile(r"([A-Z]+)(\d+)")
_RATE_CODE_RE = re.compile(r"^[A-Z]\d+(?:\.\d+)?$")
_CREDIT_COLUMN = "D"


def parse_rider18_xlsx(xlsx_bytes: bytes) -> dict[str, dict[tuple[str, str], Decimal]]:
    """Extract Rider 18 outflow credits as cents/kWh by rate, season, and period."""
    with ZipFile(BytesIO(xlsx_bytes)) as workbook:
        shared_strings = _shared_strings(workbook)
        sheet_path = _rates_sheet_path(workbook)
        if sheet_path is None:
            raise ValueError("Rider 18 workbook does not contain a Rates and Credits sheet")

        rows = _worksheet_rows(workbook, sheet_path, shared_strings)

    rates: dict[str, dict[tuple[str, str], Decimal]] = {}
    current_rate_code: str | None = None

    for row_number in sorted(rows):
        row = rows[row_number]
        label = _clean_text(row.get("B"))
        if not label:
            continue

        if _RATE_CODE_RE.match(label):
            current_rate_code = label
            rates.setdefault(current_rate_code, {})
            continue

        if current_rate_code is None:
            continue

        season_period = _season_period_from_label(label)
        if season_period is None:
            continue

        credit = _credit_cents(row.get(_CREDIT_COLUMN))
        if credit is None:
            continue

        rates.setdefault(current_rate_code, {})[season_period] = credit

    return {code: values for code, values in rates.items() if values}


def _shared_strings(workbook: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    except KeyError:
        return []

    strings: list[str] = []
    for item in root.findall("{*}si"):
        strings.append("".join(text.text or "" for text in item.findall(".//{*}t")))
    return strings


def _rates_sheet_path(workbook: ZipFile) -> str | None:
    workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
    rels_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {
        rel.attrib["Id"]: _normalize_target(rel.attrib.get("Target", ""))
        for rel in rels_root.findall("{*}Relationship")
        if "Id" in rel.attrib
    }

    fallback: str | None = None
    for sheet in workbook_root.findall(".//{*}sheet"):
        name = sheet.attrib.get("name", "")
        rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rel_targets.get(rel_id or "")
        if target is None:
            continue
        if name.strip().lower() == "rates and credits":
            return target
        if fallback is None and "rate" in name.lower():
            fallback = target
    return fallback


def _normalize_target(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join("xl", target))


def _worksheet_rows(
    workbook: ZipFile,
    sheet_path: str,
    shared_strings: list[str],
) -> dict[int, dict[str, str]]:
    root = ET.fromstring(workbook.read(sheet_path))
    rows: dict[int, dict[str, str]] = {}

    for cell in root.findall(".//{*}c"):
        ref = cell.attrib.get("r", "")
        match = _CELL_RE.match(ref)
        if not match:
            continue
        column, row_number_raw = match.groups()
        value = _cell_value(cell, shared_strings)
        if value is None:
            continue
        rows.setdefault(int(row_number_raw), {})[column] = value

    return rows


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str | None:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//{*}t"))

    value = cell.find("{*}v")
    if value is None or value.text is None:
        return None

    if cell_type == "s":
        try:
            return shared_strings[int(value.text)]
        except (IndexError, ValueError):
            return None
    return value.text


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _season_period_from_label(label: str) -> tuple[str, str] | None:
    normalized = _clean_text(label).lower().replace("-", " ")

    if "june" in normalized or "summer" in normalized or "sept" in normalized:
        season = "june_through_september"
    elif "oct" in normalized or "winter" in normalized or "may" in normalized:
        season = "october_through_may"
    else:
        return None

    if "super off peak" in normalized:
        period = "super_off_peak"
    elif "off peak" in normalized:
        period = "off_peak"
    elif "on peak" in normalized or "peak" in normalized:
        period = "peak"
    else:
        return None

    return season, period


def _credit_cents(value: Any) -> Decimal | None:
    text = _clean_text(value).replace("$", "").replace(",", "")
    if not text:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"

    try:
        return (abs(Decimal(text)) * Decimal("100")).quantize(Decimal("0.001"))
    except InvalidOperation:
        return None

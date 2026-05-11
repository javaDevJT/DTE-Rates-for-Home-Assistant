from __future__ import annotations

from decimal import Decimal, InvalidOperation
from io import BytesIO
import posixpath
import re
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile


_CELL_RE = re.compile(r"([A-Z]+)(\d+)")


def parse_pscr_cents_from_xlsx(xlsx_bytes: bytes) -> Decimal:
    """Extract the Rider 18 PSCR value as cents/kWh."""
    with ZipFile(BytesIO(xlsx_bytes)) as workbook:
        shared_strings = _shared_strings(workbook)
        sheet_path = _rates_sheet_path(workbook)
        rows = _worksheet_rows(workbook, sheet_path, shared_strings)

    for row_number in sorted(rows):
        row = rows[row_number]
        label = " ".join(row.values()).lower()
        if "pscr" not in label:
            continue

        for column in ("C", "D", "B", "E"):
            cents = _dollars_to_cents(row.get(column))
            if cents is not None:
                return cents

    raise ValueError("Rider 18 workbook does not contain a PSCR value")


def _shared_strings(workbook: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    except KeyError:
        return []

    return ["".join(text.text or "" for text in item.findall(".//{*}t")) for item in root.findall("{*}si")]


def _rates_sheet_path(workbook: ZipFile) -> str:
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

    if fallback is None:
        raise ValueError("Rider 18 workbook does not contain a rates sheet")
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
        if value is not None:
            rows.setdefault(int(row_number_raw), {})[column] = " ".join(value.split())

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


def _dollars_to_cents(value: Any) -> Decimal | None:
    text = str(value or "").replace("$", "").replace(",", "").strip()
    if not text:
        return None

    try:
        return (abs(Decimal(text)) * Decimal("100")).quantize(Decimal("0.001"))
    except InvalidOperation:
        return None

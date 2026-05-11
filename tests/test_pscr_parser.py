from __future__ import annotations

from decimal import Decimal
from html import escape
from io import BytesIO
from zipfile import ZipFile

from custom_components.dte_rates.pscr_parser import parse_pscr_cents_from_xlsx


def _xlsx_with_pscr() -> bytes:
    cells = {
        "B2": "FULL SERVICE - Rider 18 Credits",
        "B4": "PSCR (November 1, 2024)",
        "C4": "0.01877",
    }
    rows: dict[int, list[str]] = {}
    for ref, value in cells.items():
        row = int("".join(ch for ch in ref if ch.isdigit()))
        if value.replace(".", "", 1).isdigit():
            cell = f'<c r="{ref}"><v>{value}</v></c>'
        else:
            cell = f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
        rows.setdefault(row, []).append(cell)

    sheet_data = "".join(f'<row r="{row}">{"".join(cells)}</row>' for row, cells in sorted(rows.items()))
    workbook_xml = (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        '<sheet name="Rates and Credits" sheetId="1" r:id="rId1"/>'
        "</sheets>"
        "</workbook>"
    )
    rels_xml = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    sheet_xml = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{sheet_data}</sheetData>"
        "</worksheet>"
    )

    buffer = BytesIO()
    with ZipFile(buffer, "w") as workbook:
        workbook.writestr("xl/workbook.xml", workbook_xml)
        workbook.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        workbook.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def test_parse_pscr_cents_from_xlsx():
    assert parse_pscr_cents_from_xlsx(_xlsx_with_pscr()) == Decimal("1.877")

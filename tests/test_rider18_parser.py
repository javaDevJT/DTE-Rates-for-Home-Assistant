from __future__ import annotations

from decimal import Decimal
from html import escape
from io import BytesIO
from zipfile import ZipFile

from custom_components.dte_rates.rider18_parser import parse_rider18_xlsx


def _xlsx_with_rates() -> bytes:
    cells = {
        "B2": "FULL SERVICE - Rider 18 Credits",
        "G2": "FULL SERVICE - D1.11 Rate",
        "B4": "PSCR (November 1, 2024)",
        "C4": "0.01877",
        "C6": "Rider 18 Tariff (No PSCR)",
        "D6": "Outflow Cred. Incl. PSCR",
        "B7": "D1.11",
        "B8": "June-Sept On Peak",
        "C8": "-0.14407",
        "D8": "-0.16284000000000001",
        "B9": "June-Sept Off Peak",
        "D9": "-0.10586",
        "B10": "Oct-May On Peak",
        "D10": "-0.12196",
        "B11": "Oct-May Off Peak",
        "D11": "-0.10586",
    }
    rows: dict[int, list[str]] = {}
    for ref, value in cells.items():
        row = int("".join(ch for ch in ref if ch.isdigit()))
        if value.replace(".", "", 1).replace("-", "", 1).isdigit():
            cell = f'<c r="{ref}"><v>{value}</v></c>'
        else:
            cell = f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
        rows.setdefault(row, []).append(cell)

    sheet_data = "".join(f'<row r="{row}">{"".join(cells)}</row>' for row, cells in sorted(rows.items()))
    workbook_xml = (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        '<sheet name="Rider 18" sheetId="1" r:id="rId1"/>'
        '<sheet name="Rates and Credits" sheetId="3" r:id="rId3"/>'
        "</sheets>"
        "</workbook>"
    )
    rels_xml = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet3.xml"/>'
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
        workbook.writestr("xl/worksheets/sheet1.xml", "<worksheet/>")
        workbook.writestr("xl/worksheets/sheet3.xml", sheet_xml)
    return buffer.getvalue()


def test_parse_rider18_xlsx_extracts_outflow_credits_in_cents():
    rates = parse_rider18_xlsx(_xlsx_with_rates())

    assert rates == {
        "D1.11": {
            ("june_through_september", "peak"): Decimal("16.284"),
            ("june_through_september", "off_peak"): Decimal("10.586"),
            ("october_through_may", "peak"): Decimal("12.196"),
            ("october_through_may", "off_peak"): Decimal("10.586"),
        }
    }

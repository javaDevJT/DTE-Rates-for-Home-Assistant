from __future__ import annotations

from decimal import Decimal

from custom_components.dte_rates.pscr_parser import parse_pscr_rates_from_pdf


SAMPLE_RATE_BOOK_TEXT = """
C8 SURCHARGES AND CREDITS APPLICABLE TO POWER SUPPLY SERVICE
C8.5 Surcharges and Credits Applicable to Power Supply Service C-65.00
C9 SURCHARGES AND CREDITS APPLICABLE TO DELIVERY SERVICE
C9.1 Nuclear Surcharge C-66.00
C8.5 SURCHARGES AND CREDITS APPLICABLE TO POWER SUPPLY SERVICE
Rate Schedule Description PSCR Factor Other Charges
D1 Non Transmitting Meter 1.877 0.0222 0.2305 2.1297
D1.8 Dynamic Peak Pricing 1.877 0.0187 0.1934 2.0891
D1.11 Standard TOU 1.877 0.0221
D1.13 Overnight Savers 1.877 0.0221 0.2292 2.1283
Commercial
D3 General Service 1.877 0.0180 0.1867 2.0817
C9 SURCHARGES AND CREDITS APPLICABLE TO DELIVERY SERVICE
D1.11 Standard TOU 0.0890 0.4488 0.1617 0.2762
"""


class _FakePage:
    def extract_text(self):
        return SAMPLE_RATE_BOOK_TEXT


class _FakeReader:
    def __init__(self, _bytes):
        self.pages = [_FakePage()]


def test_parse_pscr_rates_from_mpsc_rate_book_pdf(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.pscr_parser.PdfReader", _FakeReader)

    assert parse_pscr_rates_from_pdf(b"fake") == {
        "D1": Decimal("1.877"),
        "D1.8": Decimal("1.877"),
        "D1.11": Decimal("1.877"),
        "D1.13": Decimal("1.877"),
        "D3": Decimal("1.877"),
    }

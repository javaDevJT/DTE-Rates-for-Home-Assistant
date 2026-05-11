from __future__ import annotations

from decimal import Decimal

from custom_components.dte_rates.pscr_parser import parse_pscr_cents_from_pdf


SAMPLE_RATE_BOOK_TEXT = """
C8.5 SURCHARGES AND CREDITS APPLICABLE TO POWER SUPPLY SERVICE
Rate Schedule Description PSCR Factor Other Charges
D1.11 Standard TOU 1.877 0.0221
D1.13 Overnight Savers 1.877 0.0221
"""


class _FakePage:
    def extract_text(self):
        return SAMPLE_RATE_BOOK_TEXT


class _FakeReader:
    def __init__(self, _bytes):
        self.pages = [_FakePage()]


def test_parse_pscr_cents_from_mpsc_rate_book_pdf(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.pscr_parser.PdfReader", _FakeReader)

    assert parse_pscr_cents_from_pdf(b"fake") == Decimal("1.877")

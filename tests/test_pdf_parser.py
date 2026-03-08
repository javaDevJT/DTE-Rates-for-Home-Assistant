from __future__ import annotations

from decimal import Decimal

from custom_components.dte_rates.pdf_parser import parse_rate_card_pdf


SAMPLE_TEXT = """
Time of Day 3 p.m. - 7 p.m. Standard Base Rate (D1.11)
Peak hours: Monday-Friday 3 p.m. to 7 p.m.
Power Supply Charges:
June through September
 All peak kWh
  Capacity Energy .................. 5.360¢ per kWh
  Non-Capacity Energy ............... 9.047¢ per kWh
 All off-peak kWh
  Capacity Energy ................... 3.240¢ per kWh
  Non-Capacity Energy ............... 5.469¢ per kWh
Delivery Charges:
 Service Charge ....................... $8.50 per month
 RIA Credit* ......................... ($8.50) per month
 Distribution kWh (Year-round) ......... 9.726¢ per kWh
Overnight Savers Rate (D1.13)
Peak hours: Monday-Friday 3 p.m. to 7 p.m.
Super off-peak hours: All kWh used between 1:00 a.m. and 7:00 a.m.
Off-peak hours: All other kWh used
Power Supply Charges:
June through September
 All peak kWh
  Capacity Energy ................... 5.949¢ per kWh
  Non-Capacity Energy .............. 10.042¢ per kWh
 All off-peak kWh
  Capacity Energy ................... 4.012¢ per kWh
  Non-Capacity Energy ............... 6.772¢ per kWh
 All super off-peak kWh
  Capacity Energy ................... 2.549¢ per kWh
  Non-Capacity Energy ............... 4.303¢ per kWh
Delivery Charges:
June through September
 Distribution peak kWh ............... 19.568¢ per kWh
 Distribution off-peak kWh ............ 14.676¢ per kWh
 Distribution super off-peak kWh ...... 4.892¢ per kWh
Dynamic Peak Pricing Rate (D1.8)
Power Supply Charges:
Peak Monday - Friday 3 p.m. to 7 p.m.
 All peak kWh
  Capacity Energy .................. 6.398¢ per kWh
  Non-Capacity Energy ............. 10.800¢ per kWh
Mid-peak Monday - Friday 7 a.m. to 3 p.m. & 7 p.m. to 11 p.m.
 All mid-peak kWh
  Capacity Energy ................... 3.305¢ per kWh
  Non-Capacity Energy ............... 5.579¢ per kWh
Off-peak 11 p.m. to 7 a.m. and all day Saturday, Sunday and designated holidays
 All off-peak kWh
  Capacity Energy ...................1.705¢ per kWh
  Non-Capacity Energy ............... 2.878¢ per kWh
Critical Peak Events occur no more than 14 weekdays per year
from 3 p.m. to 7p.m.
 All critical-peak kWh ............... 84.200¢ per kWh
  Non-Capacity Energy ............. 10.800¢ per kWh
Experimental Flex Rate (D1.99)
Ultra off-peak hours: Monday-Friday 12 a.m. to 5 a.m.
Power Supply Charges:
 All ultra off-peak kWh
  Capacity Energy ................... 1.111¢ per kWh
  Non-Capacity Energy ............... 2.222¢ per kWh
The rates on this card are approved by the Michigan Public Service Commission and are in effect as of February 6, 2025.
"""


class _FakePage:
    def extract_text(self):
        return SAMPLE_TEXT


class _FakeReader:
    def __init__(self, _bytes):
        self.pages = [_FakePage()]


REAL_D111_EXCERPT = """
Time of Day 3 p.m. - 7 p.m. Standard Base Rate (D1.11)
Peak hours: Monday-Friday 3 p.m. to 7 p.m.
Power Supply Charges:
June through September
 All peak kWh
  Capacity Energy .................. 5.360¢ per kWh
  Non-Capacity Energy ............... 9.047¢ per kWh
 All off-peak kWh
  Capacity Energy ................... 3.240¢ per kWh
  Non-Capacity Energy ............... 5.469¢ per kWh
October through May
 All peak kWh
  Capacity Energy ................... 3.839¢ per kWh
  Non-Capacity Energy .............. 6.480¢ per kWh
 All off-peak kWh
  Capacity Energy ................... 3.240¢ per kWh
  Non-Capacity Energy ............... 5.469¢ per kWh
Delivery Charges:
 Service Charge ....................... $8.50 per month
 RIA Credit* ......................... ($8.50) per month
 Distribution kWh (Year-round) ......... 9.726¢ per kWh
"""


class _RealD111Page:
    def extract_text(self):
        return REAL_D111_EXCERPT


class _RealD111Reader:
    def __init__(self, _bytes):
        self.pages = [_RealD111Page()]


def test_parse_rate_card_extracts_rates_and_effective_date(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.pdf_parser.PdfReader", _FakeReader)

    parsed = parse_rate_card_pdf(b"fake", "https://example.test/card.pdf")

    assert parsed.effective_date == "February 6, 2025"
    assert "D1.11" in parsed.rates
    assert "D1.13" in parsed.rates
    assert "D1.8" in parsed.rates
    assert "D1.99" in parsed.rates


def test_parse_rate_card_tracks_seasonal_and_period_components(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.pdf_parser.PdfReader", _FakeReader)
    parsed = parse_rate_card_pdf(b"fake", "https://example.test/card.pdf")

    d113 = parsed.rates["D1.13"]
    peak = next(p for p in d113.periods if p.period_name == "peak")
    super_off_peak = next(p for p in d113.periods if p.period_name == "super_off_peak")

    assert peak.season_name == "june_through_september"
    assert peak.components.per_kwh["capacity_energy"] == Decimal("5.949")
    assert super_off_peak.components.per_kwh["distribution_super_off_peak_kwh"] == Decimal("4.892")

    d111 = parsed.rates["D1.11"]
    d111_peak = next(p for p in d111.periods if p.period_name == "peak")
    d111_off_peak = next(p for p in d111.periods if p.period_name == "off_peak")
    assert d111_peak.components.per_kwh["distribution_kwh_year_round"] == Decimal("9.726")
    assert d111_off_peak.components.per_kwh["distribution_kwh_year_round"] == Decimal("9.726")


def test_parser_infers_time_windows_from_text(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.pdf_parser.PdfReader", _FakeReader)
    parsed = parse_rate_card_pdf(b"fake", "https://example.test/card.pdf")

    d18 = parsed.rates["D1.8"]
    mid_peak = next(p for p in d18.periods if p.period_name == "mid_peak")
    off_peak = next(p for p in d18.periods if p.period_name == "off_peak")

    assert mid_peak.window.weekdays_only is True
    assert mid_peak.window.hour_ranges == [(7, 15), (19, 23)]
    assert off_peak.window.weekends_all_day is True
    assert off_peak.window.hour_ranges == [(23, 7)]


def test_parser_supports_new_period_labels_without_code_changes(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.pdf_parser.PdfReader", _FakeReader)
    parsed = parse_rate_card_pdf(b"fake", "https://example.test/card.pdf")

    d199 = parsed.rates["D1.99"]
    ultra = next(p for p in d199.periods if p.period_name == "ultra_off_peak")

    assert ultra.window.weekdays_only is True
    assert ultra.window.hour_ranges == [(0, 5)]
    assert ultra.components.per_kwh["capacity_energy"] == Decimal("1.111")


def test_real_d111_excerpt_applies_year_round_distribution_to_all_tou_periods(monkeypatch):
    monkeypatch.setattr("custom_components.dte_rates.pdf_parser.PdfReader", _RealD111Reader)
    parsed = parse_rate_card_pdf(b"fake", "https://example.test/card.pdf")

    d111 = parsed.rates["D1.11"]
    for season in ("june_through_september", "october_through_may"):
        peak = next(p for p in d111.periods if p.season_name == season and p.period_name == "peak")
        off_peak = next(p for p in d111.periods if p.season_name == season and p.period_name == "off_peak")
        assert peak.components.per_kwh["distribution_kwh_year_round"] == Decimal("9.726")
        assert off_peak.components.per_kwh["distribution_kwh_year_round"] == Decimal("9.726")

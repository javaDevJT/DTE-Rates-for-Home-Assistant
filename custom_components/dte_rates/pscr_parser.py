from __future__ import annotations

from decimal import Decimal
import io
import re

from pypdf import PdfReader


_RATE_ROW_RE = re.compile(
    r"^\s*(?P<code>[A-Z]\d+(?:\.\d+)?)\s+.+?\s+(?P<pscr>-?\d+\.\d+)\s+\d+\.\d+",
    re.IGNORECASE,
)


def parse_pscr_rates_from_pdf(pdf_bytes: bytes) -> dict[str, Decimal]:
    """Extract current PSCR values by tariff code from the MPSC DTE electric rate book."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]

    section = _power_supply_surcharge_lines(lines)
    rates: dict[str, Decimal] = {}
    for line in section:
        match = _RATE_ROW_RE.match(line)
        if match:
            rates[match.group("code").upper()] = Decimal(match.group("pscr"))

    if not rates:
        raise ValueError("MPSC DTE rate book does not contain PSCR tariff rows")
    return rates


def _power_supply_surcharge_lines(lines: list[str]) -> list[str]:
    start = None
    for idx, line in enumerate(lines):
        lower = line.lower()
        if "c8.5 surcharges and credits applicable to power supply service" in lower:
            start = idx
            break

    if start is None:
        return lines

    end = len(lines)
    for idx in range(start + 1, len(lines)):
        lower = lines[idx].lower()
        if "c9 surcharges and credits applicable to delivery service" in lower:
            end = idx
            break

    return lines[start:end]

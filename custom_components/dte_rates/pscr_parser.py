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

    rates: dict[str, Decimal] = {}
    for section in _power_supply_surcharge_sections(lines):
        for line in section:
            match = _RATE_ROW_RE.match(line)
            if match:
                rates[match.group("code").upper()] = Decimal(match.group("pscr"))
        if rates:
            break

    if not rates:
        raise ValueError("MPSC DTE rate book does not contain PSCR tariff rows")
    return rates


def _power_supply_surcharge_sections(lines: list[str]) -> list[list[str]]:
    sections: list[list[str]] = []
    for idx, line in enumerate(lines):
        lower = line.lower()
        if "c8.5 surcharges and credits applicable to power supply service" in lower:
            end = _next_delivery_surcharge_index(lines, idx + 1)
            sections.append(lines[idx:end])

    if not sections:
        sections.append(lines)
    return sections


def _next_delivery_surcharge_index(lines: list[str], start: int) -> int:
    end = len(lines)
    for idx in range(start, len(lines)):
        lower = lines[idx].lower()
        if "c9 surcharges and credits applicable to delivery service" in lower:
            end = idx
            break
    return end

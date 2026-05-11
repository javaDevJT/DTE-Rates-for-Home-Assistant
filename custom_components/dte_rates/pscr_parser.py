from __future__ import annotations

from decimal import Decimal
import io
import re

from pypdf import PdfReader


_D111_PSCR_RE = re.compile(
    r"\bD1\.11\s+Standard\s+TOU\s+(?P<pscr>\d+\.\d+)",
    re.IGNORECASE,
)


def parse_pscr_cents_from_pdf(pdf_bytes: bytes) -> Decimal:
    """Extract the current PSCR value from the MPSC DTE electric rate book."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized = re.sub(r"\s+", " ", text)

    match = _D111_PSCR_RE.search(normalized)
    if match:
        return Decimal(match.group("pscr"))

    raise ValueError("MPSC DTE rate book does not contain a D1.11 PSCR value")

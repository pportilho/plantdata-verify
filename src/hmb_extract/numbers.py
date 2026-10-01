"""Number parsing for OCR'd engineering tables: BR and US formats, scientific notation."""

from __future__ import annotations

import re

# The exponent is exactly two digits on purpose: a greedy exponent (\d+) turns the glued
# cell "9.88E-011.00E+00" into 9.88E-011 -- a plausible, in-range, wrong value.
NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?(?:[eE][+-]?\d{2})?")

_SCIENTIFIC = re.compile(r"-?\d+(?:[.,]\d+)?[eE][+-]?\d+")
_BR_THOUSANDS = re.compile(r"-?\d{1,3}(?:\.\d{3})+,\d+")
_US_THOUSANDS = re.compile(r"-?\d{1,3}(?:,\d{3})+\.\d+")
_COMMA_DECIMAL = re.compile(r"-?\d+,\d+")
_DOT_DECIMAL = re.compile(r"-?\d+\.\d+")
_INTEGER = re.compile(r"-?\d+")


def parse_number(text: str) -> float | None:
    """Parse one cell. A comma is the decimal separator unless the text is a complete
    US-thousands number (1,234.5). Returns None for anything that is not exactly one number."""
    t = text.strip().strip("|").replace(" ", "")
    if _SCIENTIFIC.fullmatch(t):
        return float(t.replace(",", "."))
    if _BR_THOUSANDS.fullmatch(t):
        return float(t.replace(".", "").replace(",", "."))
    if _US_THOUSANDS.fullmatch(t):
        return float(t.replace(",", ""))
    if _COMMA_DECIMAL.fullmatch(t):
        return float(t.replace(",", "."))
    if _DOT_DECIMAL.fullmatch(t) or _INTEGER.fullmatch(t):
        return float(t)
    return None


def split_glued(text: str) -> list[str]:
    """Split cells that OCR glued together ("8.96E-048.96E-04" -> two cells).

    Splits only when the numbers consume (almost) the whole token and have similar
    lengths: cells of one row share a format, so very different lengths mean a wrong split."""
    if parse_number(text) is not None:
        return [text]
    parts = NUMBER.findall(text)
    if len(parts) < 2:
        return [text]
    if sum(len(p) for p in parts) < len(text) - 2:
        return [text]
    if max(len(p) for p in parts) - min(len(p) for p in parts) > 3:
        return [text]
    return parts

"""Schema of an H&MB sheet: which rows exist, their units and plausible ranges."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


class SchemaError(ValueError):
    """The schema file is invalid; the message names the offending entry."""


@dataclass(frozen=True)
class Row:
    code: str
    label: str
    unit: str
    min: float
    max: float

    def in_domain(self, value: float) -> bool:
        return self.min <= value <= self.max


@dataclass(frozen=True)
class Schema:
    quantities: tuple[Row, ...]
    components: tuple[Row, ...]
    density: dict | None
    fractions: dict | None
    stream_header: str

    @property
    def rows(self) -> tuple[Row, ...]:
        return self.quantities + self.components

    def row(self, code: str) -> Row:
        return next(r for r in self.rows if r.code == code)


def _row(entry, where: str, unit: str, lo: float, hi: float) -> Row:
    if not isinstance(entry, dict) or "code" not in entry or "label" not in entry:
        raise SchemaError(f"{where}: every row needs 'code' and 'label'")
    code = str(entry["code"])
    lo, hi = float(entry.get("min", lo)), float(entry.get("max", hi))
    if lo > hi:
        raise SchemaError(f"{where} ({code}): min {lo} > max {hi}")
    return Row(code, str(entry["label"]), str(entry.get("unit", unit)), lo, hi)


def load_schema(path) -> Schema:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    inf = float("inf")
    quantities = tuple(_row(e, f"quantities[{i}]", "", -inf, inf) for i, e in enumerate(data.get("quantities") or []))
    components = tuple(_row(e, f"components[{i}]", "-", 0.0, 1.0) for i, e in enumerate(data.get("components") or []))
    rows = quantities + components
    if not rows:
        raise SchemaError("schema has no quantities or components")

    codes = [r.code for r in rows]
    duplicates = sorted({c for c in codes if codes.count(c) > 1})
    if duplicates:
        raise SchemaError(f"duplicate codes: {', '.join(duplicates)}")
    for a in rows:
        for b in rows:
            if a.code != b.code and a.label.lower() in b.label.lower():
                raise SchemaError(f"label of {a.code!r} ({a.label!r}) is contained in label of "
                                  f"{b.code!r} ({b.label!r}); rows would be ambiguous")

    checks = data.get("checks") or {}
    density = checks.get("density")
    if density:
        for key in ("mass", "volume", "density"):
            if density.get(key) not in codes:
                raise SchemaError(f"checks.density.{key} refers to unknown code {density.get(key)!r}")
        density = {"mass": density["mass"], "volume": density["volume"], "density": density["density"],
                   "rel_tol": float(density.get("rel_tol", 0.01))}
    fractions = checks.get("fractions")
    if fractions is not None:
        if len(components) < 2:
            raise SchemaError("checks.fractions needs at least two components")
        fractions = {"abs_tol": float((fractions or {}).get("abs_tol", 0.005))}

    header = str(data.get("stream_header", r"\d{3,4}"))
    try:
        re.compile(header)
    except re.error as e:
        raise SchemaError(f"stream_header is not a valid regex: {e}") from None
    return Schema(quantities, components, density or None, fractions, header)

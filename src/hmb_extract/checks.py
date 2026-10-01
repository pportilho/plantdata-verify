"""Physics checks that do not depend on page layout.

If density = mass flow / volumetric flow and the mass fractions sum to 1, the numbers
of that stream are consistent -- no answer key needed. A missing value gives
"no_data", never "pass"."""

from __future__ import annotations

from dataclasses import dataclass, field

from .numbers import parse_number

PASS, FAIL, NO_DATA = "pass", "fail", "no_data"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: dict = field(default_factory=dict)


def as_float(value) -> float | None:
    """Numbers pass through; strings are parsed (BR/US/scientific); anything else is None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return parse_number(value)
    return None


def check_density(values: dict, spec: dict) -> CheckResult:
    m, v, rho = (as_float(values.get(spec[k])) for k in ("mass", "volume", "density"))
    if m is None or v is None or rho is None or v <= 0 or rho <= 0:
        return CheckResult("density", NO_DATA)
    calculated = m / v
    error = abs(calculated - rho) / rho
    status = PASS if error <= spec["rel_tol"] else FAIL
    return CheckResult("density", status, {"calculated": round(calculated, 6), "read": rho,
                                           "error_pct": round(error * 100, 3)})


def check_fractions(values: dict, codes: list[str], spec: dict) -> CheckResult:
    fractions = [as_float(values.get(c)) for c in codes]
    if any(f is None for f in fractions):
        return CheckResult("fractions", NO_DATA)
    total = sum(fractions)
    status = PASS if abs(total - 1.0) <= spec["abs_tol"] else FAIL
    return CheckResult("fractions", status, {"sum": round(total, 6)})


def run_checks(values: dict, schema) -> list[CheckResult]:
    results = []
    if schema.density:
        results.append(check_density(values, schema.density))
    if schema.fractions:
        results.append(check_fractions(values, [c.code for c in schema.components], schema.fractions))
    return results

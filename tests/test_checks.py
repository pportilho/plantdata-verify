from pathlib import Path

import pytest

from hmb_extract.checks import FAIL, NO_DATA, PASS, as_float, check_density, check_fractions, run_checks
from hmb_extract.schema import load_schema

SCHEMA = load_schema(Path(__file__).resolve().parents[1] / "examples" / "schema.yaml")
DENSITY = SCHEMA.density
FRACTIONS = SCHEMA.fractions
CODES = ["w_N2", "w_O2", "w_CO2", "w_H2O"]


def test_density_passes_within_tolerance():
    r = check_density({"m": 2306.51, "V": 2.5271, "rho": 912.7}, DENSITY)
    assert r.status == PASS
    assert r.detail["error_pct"] < 1


def test_density_fails_on_misread_digit():
    assert check_density({"m": 2306.51, "V": 2.5271, "rho": 812.7}, DENSITY).status == FAIL


def test_density_source_rounding_fails():
    # V printed with one significant figure: 2306.51 / 2 = 1153, not 912.7.
    assert check_density({"m": 2306.51, "V": 2.0, "rho": 912.7}, DENSITY).status == FAIL


@pytest.mark.parametrize("values", [
    {"m": 2306.51, "V": 0.0, "rho": 912.7},      # zero flow: no division, no verdict
    {"m": 2306.51, "rho": 912.7},                # missing V
    {"m": None, "V": 2.5, "rho": 912.7},
])
def test_density_without_data_is_no_data(values):
    assert check_density(values, DENSITY).status == NO_DATA


def test_fractions_pass_and_fail():
    ok = {"w_N2": 0.72, "w_O2": 0.05, "w_CO2": 0.10, "w_H2O": 0.13}
    assert check_fractions(ok, CODES, FRACTIONS).status == PASS
    bad = dict(ok, w_N2=0.12)                      # 7 read as 1
    r = check_fractions(bad, CODES, FRACTIONS)
    assert r.status == FAIL and r.detail["sum"] == pytest.approx(0.40)


def test_fractions_missing_component_is_no_data():
    assert check_fractions({"w_N2": 0.72, "w_O2": 0.05}, CODES, FRACTIONS).status == NO_DATA


def test_as_float_accepts_numeric_strings_only():
    assert as_float("912,7") == pytest.approx(912.7)
    assert as_float(3) == 3.0
    assert as_float("n/a") is None and as_float(None) is None and as_float(True) is None


def test_run_checks_order_and_string_values():
    values = {"m": "2306,51", "V": "2,5271", "rho": "912,7", "w_N2": "7.2E-01", "w_O2": 0.05, "w_CO2": 0.10, "w_H2O": 0.13}
    results = run_checks(values, SCHEMA)
    assert [(r.name, r.status) for r in results] == [("density", PASS), ("fractions", PASS)]

from pathlib import Path

import pytest

from hmb_extract.schema import SchemaError, load_schema

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "schema.yaml"


def write(tmp_path, text):
    p = tmp_path / "s.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_example_schema_loads():
    s = load_schema(EXAMPLE)
    assert [r.code for r in s.rows] == ["T", "P", "m", "V", "rho", "w_N2", "w_O2", "w_CO2", "w_H2O"]
    assert s.row("m").max == 1.0e7
    assert s.row("w_H2O").in_domain(1.0) and not s.row("w_H2O").in_domain(1.2)
    assert s.density == {"mass": "m", "volume": "V", "density": "rho", "rel_tol": 0.01}
    assert s.fractions == {"abs_tol": 0.005}
    assert s.stream_header == r"\d{3,4}"


def test_inverted_range(tmp_path):
    p = write(tmp_path, "quantities:\n  - {code: T, label: Temperature, min: 600, max: -50}\n")
    with pytest.raises(SchemaError, match=r"quantities\[0\] \(T\): min 600.0 > max -50.0"):
        load_schema(p)


def test_duplicate_code(tmp_path):
    p = write(tmp_path, "quantities:\n  - {code: T, label: Temperature}\n  - {code: T, label: Temp two}\n")
    with pytest.raises(SchemaError, match="duplicate codes: T"):
        load_schema(p)


def test_overlapping_labels_are_ambiguous(tmp_path):
    p = write(tmp_path, "quantities:\n  - {code: F, label: Flow}\n  - {code: m, label: Mass Flow}\n")
    with pytest.raises(SchemaError, match="'F'.*'m'"):
        load_schema(p)


def test_density_check_needs_known_codes(tmp_path):
    p = write(tmp_path, "quantities:\n  - {code: m, label: Mass Flow}\nchecks:\n  density: {mass: m, volume: V, density: rho}\n")
    with pytest.raises(SchemaError, match="checks.density.volume refers to unknown code 'V'"):
        load_schema(p)


def test_missing_label(tmp_path):
    p = write(tmp_path, "quantities:\n  - {code: T}\n")
    with pytest.raises(SchemaError, match=r"quantities\[0\]: every row needs 'code' and 'label'"):
        load_schema(p)


def test_empty_schema(tmp_path):
    with pytest.raises(SchemaError, match="no quantities or components"):
        load_schema(write(tmp_path, "{}\n"))


def test_bad_header_regex(tmp_path):
    p = write(tmp_path, "quantities:\n  - {code: T, label: Temperature}\nstream_header: '('\n")
    with pytest.raises(SchemaError, match="stream_header is not a valid regex"):
        load_schema(p)

import json
from pathlib import Path

from hmb_extract.cli import main

EX = Path(__file__).resolve().parents[1] / "examples"
SCHEMA = str(EX / "schema.yaml")


def test_run_on_faulty_tokens(tmp_path, capsys):
    out = tmp_path / "report.json"
    assert main(["run", str(EX / "faulty.tokens.json"), "--schema", SCHEMA, "-o", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "stream" in printed and "FAIL" in printed and "streams: 20" in printed
    report = json.loads(out.read_text())
    assert report["summary"]["density"] == {"pass": 18, "fail": 2, "no_data": 0}
    assert report["summary"]["fractions"] == {"pass": 19, "fail": 1, "no_data": 0}
    cell = report["streams"]["101"]["cells"]["T"]
    assert set(cell) == {"raw", "unit", "conf", "bbox", "bbox_label", "bbox_header"}


def test_check_accepts_llm_style_strings(tmp_path, capsys):
    records = {"streams": {
        "A": {"values": {"m": "2306,51", "V": "2,5271", "rho": "912,7",
                         "w_N2": "7.2E-01", "w_O2": 0.05, "w_CO2": 0.10, "w_H2O": 0.13}},
        "B": {"values": {"m": 2306.51, "V": "n/a", "rho": 912.7}},
    }}
    p = tmp_path / "records.json"
    p.write_text(json.dumps(records))
    assert main(["check", str(p), "--schema", SCHEMA]) == 0
    printed = capsys.readouterr().out
    assert "OK" in printed and "—" in printed


def test_check_exit_code_1_when_a_stream_fails(tmp_path):
    p = tmp_path / "records.json"
    p.write_text(json.dumps({"streams": {"A": {"values": {"m": 2306.51, "V": 2.0, "rho": 912.7}}}}))
    assert main(["check", str(p), "--schema", SCHEMA]) == 1


def test_check_rejects_wrong_shape(tmp_path, capsys):
    p = tmp_path / "records.json"
    p.write_text(json.dumps([1, 2, 3]))
    assert main(["check", str(p), "--schema", SCHEMA]) == 2
    assert "expected" in capsys.readouterr().err


def test_no_header_row_is_a_clear_error(tmp_path, capsys):
    schema = tmp_path / "s.yaml"
    schema.write_text((EX / "schema.yaml").read_text().replace(r"'\d{3,4}'", r"'S\d{3}'"))
    assert main(["run", str(EX / "clean.tokens.json"), "--schema", str(schema)]) == 2
    assert "no stream header row found" in capsys.readouterr().err


def test_bad_schema_is_a_clear_error(tmp_path, capsys):
    schema = tmp_path / "s.yaml"
    schema.write_text("quantities: []\n")
    assert main(["run", str(EX / "clean.tokens.json"), "--schema", str(schema)]) == 2
    assert "error: schema has no quantities" in capsys.readouterr().err


def test_pdf_page_out_of_range(capsys):
    assert main(["run", str(EX / "synthetic_hmb.pdf"), "--page", "9", "--schema", SCHEMA]) == 2
    err = capsys.readouterr().err
    assert "page 9 not found" in err or "pdftoppm not found" in err

import json
from pathlib import Path

import pytest

from hmb_extract.checks import PASS, run_checks
from hmb_extract.recompose import recompose
from hmb_extract.schema import load_schema
from hmb_extract.tokens import load_tokens

EX = Path(__file__).resolve().parents[1] / "examples"
SCHEMA = load_schema(EX / "schema.yaml")
TRUTH = json.loads((EX / "truth.json").read_text(encoding="utf-8"))


def run(name):
    tokens, _ = load_tokens(EX / name)
    r = recompose(tokens, SCHEMA)
    return r, {sid: run_checks(rec.values(), SCHEMA) for sid, rec in r.streams.items()}


def test_clean_sheet_matches_truth_exactly():
    r, checks = run("clean.tokens.json")
    assert list(r.streams) == list(TRUTH)
    for sid, expected in TRUTH.items():
        assert r.streams[sid].values() == pytest.approx(expected, rel=1e-12, abs=1e-15), sid
        assert [c.status for c in checks[sid]] == [PASS, PASS], sid
    assert r.discarded == []

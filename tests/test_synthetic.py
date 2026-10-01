import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

import make_synthetic as ms  # noqa: E402

from hmb_extract.checks import PASS, run_checks  # noqa: E402
from hmb_extract.schema import load_schema  # noqa: E402

SCHEMA = load_schema(ROOT / "examples" / "schema.yaml")


def test_sheet_is_deterministic():
    assert ms.build_sheet() == ms.build_sheet()
    assert list(ms.build_sheet()) == [str(s) for s in range(101, 121)]


def test_truth_is_physically_consistent():
    for sid, values in ms.truth(ms.build_sheet()).items():
        assert [r.status for r in run_checks(values, SCHEMA)] == [PASS, PASS], sid


def test_values_are_inside_schema_domains():
    for sid, values in ms.truth(ms.build_sheet()).items():
        for row in SCHEMA.rows:
            assert row.in_domain(values[row.code]), (sid, row.code)


def test_no_cell_looks_like_a_stream_id():
    for cells in ms.build_sheet().values():
        for text in cells.values():
            assert not re.fullmatch(r"\d{3,4}", text), text

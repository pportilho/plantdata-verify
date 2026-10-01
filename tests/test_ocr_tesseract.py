from pathlib import Path

import pytest

from hmb_extract.ocr import OcrUnavailable, get_backend
from hmb_extract.recompose import recompose
from hmb_extract.schema import load_schema

EX = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.ocr
def test_tesseract_finds_every_stream():
    try:
        tokens = get_backend("tesseract")(EX / "synthetic_hmb.png")
    except OcrUnavailable as e:
        pytest.skip(str(e))
    r = recompose(tokens, load_schema(EX / "schema.yaml"))
    assert len(r.streams) == 20

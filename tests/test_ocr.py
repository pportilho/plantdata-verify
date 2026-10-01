import shutil
import sys
from pathlib import Path

import pytest

from hmb_extract import ocr
from hmb_extract.ocr import OcrUnavailable, get_backend, rasterize

PDF = Path(__file__).resolve().parents[1] / "examples" / "synthetic_hmb.pdf"


def test_unknown_backend():
    with pytest.raises(OcrUnavailable, match="unknown OCR backend 'nope'"):
        get_backend("nope")


def test_vision_needs_macos(monkeypatch):
    from hmb_extract.ocr import vision
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(OcrUnavailable, match="needs macOS"):
        vision.ocr_image(Path("x.png"))


def test_vision_missing_helper_explains_build(monkeypatch, tmp_path):
    from hmb_extract.ocr import vision
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HMB_VISION_BIN", str(tmp_path / "missing"))
    with pytest.raises(OcrUnavailable, match="swiftc -O swift/ocr_tokens.swift"):
        vision.ocr_image(Path("x.png"))


def test_rasterize_without_poppler(monkeypatch):
    monkeypatch.setattr(ocr.shutil, "which", lambda name: None)
    with pytest.raises(OcrUnavailable, match="pdftoppm not found"):
        rasterize(PDF)


@pytest.mark.skipif(shutil.which("pdftoppm") is None, reason="poppler not installed")
def test_rasterize_page_out_of_range():
    with pytest.raises(OcrUnavailable, match="page 9 not found in synthetic_hmb.pdf"):
        rasterize(PDF, page=9)


@pytest.mark.skipif(shutil.which("pdftoppm") is None, reason="poppler not installed")
def test_rasterize_first_page():
    png = rasterize(PDF, page=1, dpi=200)
    assert png.suffix == ".png" and png.stat().st_size > 0

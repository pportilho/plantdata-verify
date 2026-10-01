"""OCR backends: image -> tokens. A backend is a function (Path) -> list[Token]."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class OcrUnavailable(RuntimeError):
    """The requested OCR engine, or the PDF rasterizer, is not available."""


def get_backend(name: str = "auto"):
    if name == "auto":
        name = "vision" if sys.platform == "darwin" else "tesseract"
    if name == "vision":
        from .vision import ocr_image
    elif name == "tesseract":
        from .tesseract import ocr_image
    else:
        raise OcrUnavailable(f"unknown OCR backend {name!r}")
    return ocr_image


def rasterize(pdf: Path, page: int = 1, dpi: int = 200) -> Path:
    """One PDF page -> PNG with poppler's pdftoppm. 200 dpi is deliberate: Apple Vision
    downsizes large images internally, so a higher dpi reads worse."""
    exe = shutil.which("pdftoppm")
    if not exe:
        raise OcrUnavailable("pdftoppm not found: install poppler (brew install poppler / apt install poppler-utils)")
    out_dir = Path(tempfile.mkdtemp(prefix="hmb-"))
    subprocess.run([exe, "-r", str(dpi), "-png", "-f", str(page), "-l", str(page), str(pdf), str(out_dir / "p")],
                   capture_output=True)
    pngs = sorted(out_dir.glob("p*.png"))
    if not pngs:
        raise OcrUnavailable(f"page {page} not found in {Path(pdf).name}")
    return pngs[0]

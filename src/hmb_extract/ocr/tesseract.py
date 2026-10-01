"""Tesseract backend (Linux, Windows, macOS): pip install "hmb-extract[ocr]" + the tesseract binary."""

from __future__ import annotations

from pathlib import Path

from ..tokens import Token
from . import OcrUnavailable


def ocr_image(image: Path) -> list[Token]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise OcrUnavailable('the Tesseract backend needs: pip install "hmb-extract[ocr]"') from None
    try:
        # psm 11 = sparse text: tables are islands of words, not paragraphs.
        d = pytesseract.image_to_data(Image.open(image), config="--psm 11", output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError:
        raise OcrUnavailable("tesseract not found: brew install tesseract / apt install tesseract-ocr") from None
    tokens = []
    for text, conf, x, y, w, h in zip(d["text"], d["conf"], d["left"], d["top"], d["width"], d["height"]):
        if text.strip() and float(conf) >= 0:
            tokens.append(Token(text.strip(), float(x), float(y), float(x + w), float(y + h), conf=float(conf) / 100))
    return tokens

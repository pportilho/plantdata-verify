"""Apple Vision (macOS) through a small Swift helper: swift/ocr_tokens.swift."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ..tokens import Token
from . import OcrUnavailable

REPO_BINARY = Path(__file__).resolve().parents[3] / "build" / "ocr_tokens"
BUILD_HINT = "swiftc -O swift/ocr_tokens.swift -o build/ocr_tokens"


def _binary() -> Path:
    if sys.platform != "darwin":
        raise OcrUnavailable("Apple Vision needs macOS; use --ocr tesseract")
    path = Path(os.environ.get("HMB_VISION_BIN", REPO_BINARY))
    if not path.exists():
        raise OcrUnavailable(f"Vision helper not built. From the repo root run: {BUILD_HINT}")
    return path


def ocr_image(image: Path) -> list[Token]:
    out = subprocess.run([str(_binary()), str(image)], capture_output=True, text=True, check=True)
    fields = Token.__dataclass_fields__
    return [Token(**{k: v for k, v in t.items() if k in fields}) for t in json.loads(out.stdout)["tokens"]]

"""Synthetic heat & material balance sheet: flue gas and condensate, 20 streams.

Rendered as an IMAGE-ONLY PDF -- the hard case this tool exists for: there is no text
layer, OCR is the only way in. Values are internally consistent (V = m / rho, mass
fractions sum to 1) and truth.json stores them exactly as printed.

Run from the repo root:  python examples/make_synthetic.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from hmb_extract.numbers import parse_number

HERE = Path(__file__).resolve().parent
STREAMS = [str(s) for s in range(101, 121)]
LIQUID = {"105", "110", "115", "120"}

# Layout in pixels. If OCR misreads the clean sheet, tune these -- never the parser.
FONT_SIZE = 22
WIDTH, HEIGHT = 2520, 1120
LABEL_X = 40
FIRST_COLUMN_X, COLUMN_STEP = 720, 180
BLOCK_TOPS = (110, 620)
ROW_STEP = 45

ROWS = [
    ("T", "Temperature (°C)"),
    ("P", "Pressure (barg)"),
    ("m", "Mass Flow (kg/h)"),
    ("V", "Volumetric Flow (m3/h)"),
    ("rho", "Density (kg/m3)"),
    ("w_N2", "Mass Fraction Nitrogen"),
    ("w_O2", "Mass Fraction Oxygen"),
    ("w_CO2", "Mass Fraction Carbon Dioxide"),
    ("w_H2O", "Mass Fraction Water"),
]


def stream_texts(rng: random.Random, sid: str) -> dict[str, str]:
    """Printed cell texts for one stream: decimal comma for properties and flows,
    scientific notation for mass fractions (as on many EPC datasheets)."""
    if sid in LIQUID:
        t, p = rng.uniform(40, 95), rng.uniform(1.0, 10.0)
        rho, m = rng.uniform(960, 995), rng.uniform(500, 5000)
        w = {"w_N2": 0.0, "w_O2": 0.0, "w_CO2": 0.0}
    else:
        t, p = rng.uniform(120, 450), rng.uniform(0.02, 0.5)
        rho, m = rng.uniform(0.45, 0.95), rng.uniform(5000, 60000)
        w = {"w_N2": rng.uniform(0.70, 0.75), "w_O2": rng.uniform(0.03, 0.06), "w_CO2": rng.uniform(0.08, 0.12)}
    texts = {"T": f"{t:.1f}", "P": f"{p:.2f}", "m": f"{m:.2f}", "rho": f"{rho:.4f}"}
    v = float(texts["m"]) / float(texts["rho"])  # V derives from the PRINTED m and rho
    texts["V"] = f"{v:.4f}" if v < 100 else f"{v:.2f}"
    texts = {k: x.replace(".", ",") for k, x in texts.items()}
    fractions = {k: f"{x:.4E}" for k, x in w.items()}
    fractions["w_H2O"] = f"{1.0 - sum(float(x) for x in fractions.values()):.4E}"
    return {**texts, **fractions}


def build_sheet(seed: int = 42) -> dict[str, dict[str, str]]:
    rng = random.Random(seed)
    return {sid: stream_texts(rng, sid) for sid in STREAMS}


def truth(sheet: dict[str, dict[str, str]]) -> dict[str, dict[str, float]]:
    return {sid: {code: parse_number(text) for code, text in cells.items()} for sid, cells in sheet.items()}


def render(sheet: dict[str, dict[str, str]], png: Path, pdf: Path) -> None:
    font = ImageFont.load_default(size=FONT_SIZE)
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    def centered(cx: float, y: float, text: str) -> None:
        draw.text((cx - draw.textlength(text, font=font) / 2, y), text, font=font, fill="black")

    draw.text((LABEL_X, 30), "HEAT AND MATERIAL BALANCE - SYNTHETIC EXAMPLE", font=font, fill="black")
    for top, block in zip(BLOCK_TOPS, (STREAMS[:10], STREAMS[10:])):
        draw.text((LABEL_X, top), "Stream", font=font, fill="black")
        for j, sid in enumerate(block):
            centered(FIRST_COLUMN_X + j * COLUMN_STEP, top, sid)
        for k, (code, label) in enumerate(ROWS, start=1):
            y = top + k * ROW_STEP
            draw.text((LABEL_X, y), label, font=font, fill="black")
            for j, sid in enumerate(block):
                centered(FIRST_COLUMN_X + j * COLUMN_STEP, y, sheet[sid][code])
    img.save(png)
    img.save(pdf, "PDF", resolution=200)


def main() -> None:
    sheet = build_sheet()
    render(sheet, HERE / "synthetic_hmb.png", HERE / "synthetic_hmb.pdf")
    (HERE / "truth.json").write_text(json.dumps(truth(sheet), indent=1), encoding="utf-8")
    print(f"wrote {len(sheet)} streams to {HERE.name}/")


if __name__ == "__main__":
    main()

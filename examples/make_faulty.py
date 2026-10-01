"""Inject faults into the clean OCR tokens, reproducing defects seen in real documents.

Three faults the pipeline must REPAIR (glued cells, glued cells with the greedy-exponent
trap, a truncated row label) and three it cannot repair but the physics checks must FLAG
(source rounding, two misread digits).

Run from the repo root:  python examples/make_faulty.py
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from hmb_extract.recompose import recompose
from hmb_extract.schema import load_schema
from hmb_extract.tokens import load_tokens, save_tokens

HERE = Path(__file__).resolve().parent
# Plausible OCR confusions for the first significant digit.
MISREAD = {"1": "7", "2": "7", "3": "8", "4": "9", "5": "6", "6": "5", "7": "1", "8": "3", "9": "4"}
NO_PARENT = dict(parent=None, offset=None, parent_x0=None, parent_x1=None, parent_len=None)


def misread(text: str) -> str:
    for i, ch in enumerate(text):
        if ch in MISREAD:
            return text[:i] + MISREAD[ch] + text[i + 1:]
    raise ValueError(f"no significant digit in {text!r}")


def inject(tokens, schema):
    cells = recompose(tokens, schema).streams
    toks = list(tokens)
    notes: list[str] = []

    def index(sid, code):
        # Same text, nearest center: robust to the box repairs recompose applied.
        cell = cells[sid].cells[code]
        cx, cy = (cell.bbox[0] + cell.bbox[2]) / 2, (cell.bbox[1] + cell.bbox[3]) / 2
        same = [i for i, t in enumerate(toks) if t.text.strip().strip("|").strip() == cell.raw]
        return min(same, key=lambda i: abs(toks[i].x - cx) + abs(toks[i].y - cy))

    def glue(a_sid, b_sid, code, why):
        ia, ib = index(a_sid, code), index(b_sid, code)
        a, b = toks[ia], toks[ib]
        toks[ia] = replace(a, text=a.text + b.text, x1=b.x1, y0=min(a.y0, b.y0), y1=max(a.y1, b.y1),
                           conf=min(a.conf, b.conf), **NO_PARENT)
        del toks[ib]
        notes.append(f"repair: {code} of {a_sid}+{b_sid} glued as {toks[ia].text!r} ({why})")

    def retext(sid, code, text, why):
        i = index(sid, code)
        notes.append(f"flag: {code} of {sid} {toks[i].text!r} -> {text!r} ({why})")
        toks[i] = replace(toks[i], text=text)

    # Faults the checks must flag.
    v = cells["105"].cells["V"].value
    rounded = round(v)
    assert rounded > 0 and abs(rounded - v) / v > 0.02, "pick another liquid stream"
    retext("105", "V", str(rounded), "source printed V with one significant figure")
    retext("117", "rho", misread(cells["117"].cells["rho"].raw), "misread digit")
    retext("109", "w_N2", misread(cells["109"].cells["w_N2"].raw), "misread digit")

    # Faults the pipeline must repair.
    glue("102", "103", "w_N2", "cells read without a separator")
    glue("112", "113", "w_O2", "a greedy exponent would swallow the next cell's first digit")
    block2_top = min(t.y for t in toks if t.text == "111")
    dioxide = next(t for t in toks if t.text == "Dioxide" and t.y > block2_top)
    toks.remove(dioxide)
    notes.append("repair: row label 'Mass Fraction Carbon Dioxide' truncated to '... Carbon' in block 2")
    return toks, notes


def main() -> None:
    schema = load_schema(HERE / "schema.yaml")
    tokens, meta = load_tokens(HERE / "clean.tokens.json")
    faulty, notes = inject(tokens, schema)
    save_tokens(HERE / "faulty.tokens.json", faulty, width=meta.get("width"), height=meta.get("height"),
                injected=notes)
    print("\n".join(notes))


if __name__ == "__main__":
    main()

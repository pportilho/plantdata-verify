"""Results as JSON for machines and as a compact table for people."""

from __future__ import annotations

import json
from pathlib import Path

from .checks import FAIL, NO_DATA, PASS

MARK = {PASS: "OK", FAIL: "FAIL", NO_DATA: "·"}


def summarize(checks_by_stream: dict) -> dict:
    out: dict[str, dict[str, int]] = {}
    for results in checks_by_stream.values():
        for r in results:
            out.setdefault(r.name, {PASS: 0, FAIL: 0, NO_DATA: 0})[r.status] += 1
    return out


def build_report(recomp, checks_by_stream: dict, source: dict) -> dict:
    return {
        "source": source,
        "summary": summarize(checks_by_stream),
        "streams": {
            sid: {
                "values": rec.values(),
                "cells": {code: {"raw": c.raw, "unit": c.unit, "conf": c.conf, "bbox": c.bbox,
                                 "bbox_label": c.bbox_label, "bbox_header": c.bbox_header}
                          for code, c in rec.cells.items()},
                "checks": [{"name": r.name, "status": r.status, **r.detail} for r in checks_by_stream.get(sid, [])],
            }
            for sid, rec in recomp.streams.items()
        },
        "discarded": [vars(d) for d in recomp.discarded],
    }


def format_table(values_by_stream: dict, checks_by_stream: dict, codes: list[str]) -> str:
    names = sorted({r.name for results in checks_by_stream.values() for r in results})
    head = ["stream", *codes, *names]
    rows = []
    for sid in sorted(values_by_stream):
        values = values_by_stream[sid]
        marks = {r.name: MARK[r.status] for r in checks_by_stream.get(sid, [])}
        rows.append([sid, *[f"{values[c]:.6g}" if values.get(c) is not None else "—" for c in codes],
                     *[marks.get(n, "·") for n in names]])
    widths = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
    line = lambda cells: "  ".join(str(x).rjust(w) for x, w in zip(cells, widths))  # noqa: E731
    return "\n".join([line(head), line(["-" * w for w in widths]), *(line(r) for r in rows)])


def write_json(path, data: dict) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

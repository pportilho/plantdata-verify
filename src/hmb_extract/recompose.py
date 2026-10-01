"""Rebuild process streams from OCR tokens, anchored on the schema -- not on pixels.

Geometry is only a hypothesis for "which value belongs to which row and column".
A value enters a record only if it passes its row's domain test, and a record is only
trusted if the physics checks close (checks.py)."""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

from .numbers import parse_number
from .tokens import Token, clean_and_split, fix_colliding_boxes

# Layout tolerances, in multiples of the median text height.
LABEL_COLUMN_WIDTH = 25   # the label column spans this many text heights from the left edge
LINE_GAP = 0.5            # tokens closer than this vertically are on the same line
SAME_ROW = 0.7            # a value belongs to a label whose center is this close vertically
MAX_COLUMN_OFFSET = 5     # a value belongs to the nearest stream header within this distance
MIN_HEADERS = 5           # a line with at least this many stream IDs is a table header


@dataclass
class Cell:
    value: float
    raw: str
    unit: str
    conf: float
    bbox: list
    bbox_label: list
    bbox_header: list
    dx: float = field(repr=False)  # distance to the header column; keeps the best candidate


@dataclass
class StreamRecord:
    stream: str
    cells: dict = field(default_factory=dict)

    def values(self) -> dict:
        return {code: c.value for code, c in self.cells.items()}


@dataclass
class Discard:
    text: str
    bbox: list
    row: str
    stream: str
    reason: str


@dataclass
class Recomposition:
    streams: dict
    discarded: list
    labels_found: int
    header_rows_found: int


def _lines(tokens: list[Token], gap: float) -> list[list[Token]]:
    """Group tokens into text lines: sorted by y, a new line starts after a jump > gap."""
    lines: list[list[Token]] = []
    for t in sorted(tokens, key=lambda t: t.y):
        if lines and t.y - lines[-1][-1].y <= gap:
            lines[-1].append(t)
        else:
            lines.append([t])
    return lines


def _box(tokens: list[Token]) -> list[int]:
    return [round(min(t.x0 for t in tokens)), round(min(t.y0 for t in tokens)),
            round(max(t.x1 for t in tokens)), round(max(t.y1 for t in tokens))]


def recompose(tokens, schema) -> Recomposition:
    toks = clean_and_split(fix_colliding_boxes(tokens))
    if not toks:
        return Recomposition({}, [], 0, 0)
    h = statistics.median(t.height for t in toks) or 20.0
    header_re = re.compile(schema.stream_header)

    # 1. Row labels: non-numeric tokens in the left column, joined per text line.
    left_edge = min(t.x0 for t in toks)
    label_toks = [t for t in toks if t.x0 < left_edge + h * LABEL_COLUMN_WIDTH and parse_number(t.text) is None]
    labels = []
    for line in _lines(label_toks, h * LINE_GAP):
        line.sort(key=lambda t: t.x)
        text = " ".join(t.text for t in line).lower()
        row = next((r for r in schema.rows if r.label.lower() in text), None)
        if row is not None:
            labels.append({"row": row, "y": statistics.median(t.y for t in line),
                           "x_end": max(t.x1 for t in line), "bbox": _box(line)})

    # 2. Header rows: lines with >= MIN_HEADERS stream IDs. Each one starts a table block.
    header_toks = [t for t in toks if header_re.fullmatch(t.text)]
    blocks = sorted((statistics.median(t.y for t in line), line)
                    for line in _lines(header_toks, h * LINE_GAP) if len(line) >= MIN_HEADERS)

    # 3. Values: on the label's line, right of the label, under the nearest header.
    # Every stream ID found in a header row gets a record, even if all its values
    # are later discarded: "found but out of range" must stay distinguishable from
    # "never found".
    streams: dict[str, StreamRecord] = {}
    for _, headers in blocks:
        for head in headers:
            streams.setdefault(head.text, StreamRecord(head.text))
    discarded: list[Discard] = []
    for label in labels:
        above = [b for b in blocks if b[0] < label["y"]]
        if not above:
            continue
        headers, row = above[-1][1], label["row"]
        for t in toks:
            if header_re.fullmatch(t.text):
                continue
            value = parse_number(t.text)
            if value is None or abs(t.y - label["y"]) > h * SAME_ROW or t.x0 < label["x_end"] + h * 0.5:
                continue
            head = min(headers, key=lambda hd: abs(hd.x - t.x))
            dx = abs(head.x - t.x)
            if dx > h * MAX_COLUMN_OFFSET:
                continue
            if not row.in_domain(value):
                discarded.append(Discard(t.text, t.bbox(), row.code, head.text,
                                         f"outside {row.min:g}..{row.max:g} {row.unit}".strip()))
                continue
            record = streams.setdefault(head.text, StreamRecord(head.text))
            previous = record.cells.get(row.code)
            if previous is None or dx < previous.dx:
                record.cells[row.code] = Cell(value, t.text, row.unit, round(t.conf, 3), t.bbox(),
                                              label["bbox"], head.bbox(), dx)
    return Recomposition(dict(sorted(streams.items())), discarded, len(labels), len(blocks))

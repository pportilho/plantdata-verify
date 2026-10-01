"""OCR tokens: one box per word or number, in image pixels (origin top-left)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

from .numbers import split_glued


@dataclass(frozen=True)
class Token:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    conf: float = 1.0
    # Optional position inside the OCR line the token came from (the Vision helper
    # emits these; they repair boxes Vision reports twice -- see fix_colliding_boxes).
    parent: int | None = None
    offset: int | None = None
    parent_x0: float | None = None
    parent_x1: float | None = None
    parent_len: int | None = None

    @property
    def x(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def y(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def bbox(self) -> list[int]:
        return [round(self.x0), round(self.y0), round(self.x1), round(self.y1)]


_FIELDS = {f.name for f in fields(Token)}


def load_tokens(path) -> tuple[list[Token], dict]:
    """Read a token file. Unknown fields are ignored; a missing conf means 1.0."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    tokens = [Token(**{k: v for k, v in t.items() if k in _FIELDS}) for t in data["tokens"]]
    meta = {k: v for k, v in data.items() if k != "tokens"}
    return tokens, meta


def save_tokens(path, tokens, **meta) -> None:
    data = dict(meta, tokens=[{k: v for k, v in asdict(t).items() if v is not None} for t in tokens])
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def fix_colliding_boxes(tokens) -> list[Token]:
    """Vision sometimes returns the same box for different substrings of one line
    (about 4% of tokens on a real sheet). When that happens, rebuild x from the
    character offset inside the parent line."""
    by_parent: dict[int, list[Token]] = {}
    for t in tokens:
        if t.parent is not None:
            by_parent.setdefault(t.parent, []).append(t)
    fixed: dict[int, Token] = {}
    for line in by_parent.values():
        same_box: dict[tuple[int, int], list[Token]] = {}
        for t in line:
            same_box.setdefault((round(t.x0), round(t.x1)), []).append(t)
        for group in same_box.values():
            if len(group) < 2:
                continue
            for t in group:
                if None in (t.offset, t.parent_x0, t.parent_x1) or not t.parent_len:
                    continue
                char_w = (t.parent_x1 - t.parent_x0) / t.parent_len
                fixed[id(t)] = replace(t, x0=t.parent_x0 + char_w * t.offset,
                                       x1=t.parent_x0 + char_w * (t.offset + len(t.text)))
    return [fixed.get(id(t), t) for t in tokens]


def clean_and_split(tokens) -> list[Token]:
    """Strip table-rule characters and split glued numeric cells, sharing the box
    in proportion to character count."""
    out: list[Token] = []
    for tok in tokens:
        text = tok.text.strip().strip("|").strip()
        if not text:
            continue
        parts = split_glued(text)
        if len(parts) == 1:
            out.append(replace(tok, text=text))
            continue
        width, total, pos = tok.x1 - tok.x0, sum(len(p) for p in parts), 0
        for p in parts:
            x0 = tok.x0 + width * pos / total
            pos += len(p)
            out.append(replace(tok, text=p, x0=x0, x1=tok.x0 + width * pos / total))
    return out

import json

from hmb_extract.tokens import Token, clean_and_split, fix_colliding_boxes, load_tokens, save_tokens


def test_load_defaults_conf_and_ignores_unknown_fields(tmp_path):
    p = tmp_path / "t.json"
    p.write_text(json.dumps({"width": 10, "tokens": [{"text": "101", "x0": 0, "y0": 0, "x1": 5, "y1": 2, "extra": 1}]}))
    tokens, meta = load_tokens(p)
    assert tokens == [Token("101", 0, 0, 5, 2)]
    assert tokens[0].conf == 1.0
    assert meta == {"width": 10}


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "t.json"
    toks = [Token("185,3", 1.5, 2.0, 3.5, 4.0, conf=0.9, parent=3, offset=0, parent_x0=1.0, parent_x1=9.0, parent_len=12)]
    save_tokens(p, toks, width=100, height=50)
    loaded, meta = load_tokens(p)
    assert loaded == toks
    assert meta == {"width": 100, "height": 50}


def test_geometry_helpers():
    t = Token("x", 10, 20, 30, 40)
    assert (t.x, t.y, t.height) == (20, 30, 20)
    assert t.bbox() == [10, 20, 30, 40]


def test_clean_strips_rules_and_drops_empty():
    out = clean_and_split([Token("|4,70|", 0, 0, 10, 10), Token(" | ", 0, 0, 1, 1)])
    assert [t.text for t in out] == ["4,70"]


def test_clean_splits_glued_cells_proportionally():
    out = clean_and_split([Token("8.96E-048.96E-04", 0, 0, 160, 20)])
    assert [t.text for t in out] == ["8.96E-04", "8.96E-04"]
    assert (out[0].x0, out[0].x1, out[1].x0, out[1].x1) == (0, 80, 80, 160)


def test_fix_colliding_boxes_uses_character_offset():
    # Vision returned the same box for two different words of one 20-char line.
    a = Token("12,5", 100, 0, 140, 20, parent=1, offset=0, parent_x0=100.0, parent_x1=300.0, parent_len=20)
    b = Token("7,25", 100, 0, 140, 20, parent=1, offset=10, parent_x0=100.0, parent_x1=300.0, parent_len=20)
    fa, fb = fix_colliding_boxes([a, b])
    assert (fa.x0, fa.x1) == (100.0, 140.0)
    assert (fb.x0, fb.x1) == (200.0, 240.0)


def test_fix_colliding_boxes_keeps_distinct_boxes():
    a = Token("1", 0, 0, 10, 10, parent=1, offset=0, parent_x0=0.0, parent_x1=100.0, parent_len=10)
    b = Token("2", 50, 0, 60, 10, parent=1, offset=5, parent_x0=0.0, parent_x1=100.0, parent_len=10)
    assert fix_colliding_boxes([a, b]) == [a, b]

from pathlib import Path

from hmb_extract.recompose import recompose
from hmb_extract.schema import load_schema
from hmb_extract.tokens import Token

SCHEMA = load_schema(Path(__file__).resolve().parents[1] / "examples" / "schema.yaml")
H = 20  # text height in the fixtures


def left(text, x, y):
    return Token(text, x, y - H / 2, x + 11 * len(text), y + H / 2)


def centered(text, cx, y):
    w = 11 * len(text)
    return Token(text, cx - w / 2, y - H / 2, cx + w / 2, y + H / 2)


def table(top, streams, rows):
    """Header 'Stream' + IDs at `top`; each row = (label, [cell texts]) 45 px apart."""
    toks = [left("Stream", 40, top)]
    toks += [centered(s, 720 + j * 180, top) for j, s in enumerate(streams)]
    for k, (label, cells) in enumerate(rows, start=1):
        y = top + 45 * k
        toks += [left(word, 40 + 12 * len(" ".join(label.split()[:i])) + (12 if i else 0), y)
                 for i, word in enumerate(label.split())]
        toks += [centered(c, 720 + j * 180, y) for j, c in enumerate(cells)]
    return toks


STREAMS = ["101", "102", "103", "104", "105"]


def test_one_block_with_provenance():
    toks = table(100, STREAMS, [("Temperature (°C)", ["185,3", "40,0", "210,5", "95,1", "60,2"]),
                                ("Density (kg/m3)", ["0,6234", "975,1", "0,55", "980,2", "0,71"])])
    r = recompose(toks, SCHEMA)
    assert list(r.streams) == STREAMS
    assert r.streams["101"].values() == {"T": 185.3, "rho": 0.6234}
    cell = r.streams["103"].cells["T"]
    assert cell.raw == "210,5" and cell.unit == "°C"
    assert cell.bbox_header == centered("103", 720 + 2 * 180, 100).bbox()
    assert (r.labels_found, r.header_rows_found, r.discarded) == (2, 1, [])


def test_rows_belong_to_the_block_above():
    toks = table(100, STREAMS, [("Temperature (°C)", ["1,0", "2,0", "3,0", "4,0", "5,0"])])
    toks += table(400, ["111", "112", "113", "114", "115"], [("Temperature (°C)", ["11,0", "12,0", "13,0", "14,0", "15,0"])])
    r = recompose(toks, SCHEMA)
    assert r.streams["101"].values()["T"] == 1.0
    assert r.streams["115"].values()["T"] == 15.0
    assert r.header_rows_found == 2


def test_out_of_domain_value_is_discarded_and_reported():
    toks = table(100, STREAMS, [("Temperature (°C)", ["185,3", "9000,0", "210,5", "95,1", "60,2"])])
    r = recompose(toks, SCHEMA)
    assert "T" not in r.streams["102"].cells
    [d] = r.discarded
    assert (d.text, d.row, d.stream) == ("9000,0", "T", "102")
    assert "outside" in d.reason


def test_glued_cells_are_split_into_their_columns():
    toks = table(100, STREAMS, [("Mass Fraction Nitrogen", ["7.2345E-01", "7.1234E-01", "7.3E-01", "7.4E-01", "7.5E-01"])])
    a = next(t for t in toks if t.text == "7.2345E-01")
    b = next(t for t in toks if t.text == "7.1234E-01")
    toks = [t for t in toks if t not in (a, b)] + [Token(a.text + b.text, a.x0, a.y0, b.x1, b.y1)]
    r = recompose(toks, SCHEMA)
    assert r.streams["101"].values()["w_N2"] == 0.72345
    assert r.streams["102"].values()["w_N2"] == 0.71234


def test_truncated_label_still_matches_shortest_label():
    toks = table(100, STREAMS, [("Mass Fraction Carbon", ["1.0E-01"] * 5)])
    assert recompose(toks, SCHEMA).streams["104"].values() == {"w_CO2": 0.1}


def test_no_header_row_gives_no_streams():
    toks = [left("Temperature", 40, 100), centered("185,3", 720, 100)]
    r = recompose(toks, SCHEMA)
    assert (r.streams, r.header_rows_found) == ({}, 0)


def test_empty_input():
    assert recompose([], SCHEMA).streams == {}

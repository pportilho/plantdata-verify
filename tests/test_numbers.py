import pytest

from hmb_extract.numbers import parse_number, split_glued


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2306,5100", 2306.51),
        ("12.450,30", 12450.30),
        ("1.234.567,89", 1234567.89),
        ("12,450.30", 12450.30),
        ("0.6234", 0.6234),
        ("185", 185.0),
        ("-1,5", -1.5),
        ("7.1234E-01", 0.71234),
        ("9,88E-01", 0.988),
        ("|4,7000|", 4.7),
    ],
)
def test_parse_number_formats(text, expected):
    assert parse_number(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["Temperature", "kg/h", "", "1.2.3", "8.96E-048.96E-04"])
def test_parse_number_rejects_non_numbers(text):
    assert parse_number(text) is None


def test_split_glued_cells():
    # Real defect 1: two cells read without a separator.
    assert split_glued("8.96E-048.96E-04") == ["8.96E-04", "8.96E-04"]


def test_split_greedy_exponent_regression():
    # Real defect 2: a greedy exponent (\d+) reads 9.88E-011 -- plausible, in range,
    # and ten orders of magnitude wrong. The exponent must stop at two digits.
    assert split_glued("9.88E-011.00E+00") == ["9.88E-01", "1.00E+00"]


def test_split_keeps_single_numbers():
    assert split_glued("1.234.567,89") == ["1.234.567,89"]
    assert split_glued("2306,5100") == ["2306,5100"]


def test_split_refuses_dissimilar_lengths():
    # Cells of one row share a format; very different lengths mean a wrong split.
    assert split_glued("12.450,30x") == ["12.450,30x"]


def test_split_leaves_text_alone():
    assert split_glued("Temperature") == ["Temperature"]

# hmb-extract

**Extract process tables from scanned engineering PDFs, then verify every stream with physics — not with a hand-typed answer key.**

[![ci](https://github.com/pportilho/hmb-extract/actions/workflows/ci.yml/badge.svg)](https://github.com/pportilho/hmb-extract/actions/workflows/ci.yml)

## The problem

Heat & material balance (H&MB) sheets often arrive as PDFs whose text was converted to outlines: there is nothing to copy, and `pdfplumber` or `camelot` see no text at all.
OCR gets the characters back but loses the table — which number belongs to which stream becomes a guess.
Worse, extraction fails *silently*: a misread digit is still a plausible number.
And checking against a hand-typed answer key only covers the cells you chose to check.

## The idea

1. **Anchor on the process model, not on pixels.** A schema says which rows exist, their units and plausible ranges. Each column becomes one process stream — the way an engineer reads the sheet.
2. **Domain test per row.** A "temperature" of 9,000 °C is not a temperature: it is discarded and reported, never kept silently.
3. **Physics closes the loop.** Two checks that do not depend on layout:
   - density = mass flow / volumetric flow
   - mass fractions sum to 1

   When both close, that stream's numbers are consistent. When one fails, it points at the stream to look at.

## 60-second demo (no OCR needed)

```bash
git clone https://github.com/pportilho/hmb-extract && cd hmb-extract
python -m venv .venv && . .venv/bin/activate
pip install -e .
hmb-extract run examples/faulty.tokens.json --schema examples/schema.yaml
```

<!-- demo:start -->
```text
stream      T     P        m        V      rho     w_N2      w_O2     w_CO2     w_H2O  density  fractions
------  -----  ----  -------  -------  -------  -------  --------  --------  --------  -------  ---------
   101    331  0.03  17276.6    29407   0.5875  0.73682  0.050301   0.11569  0.097189       OK         OK
   102  148.7  0.22  17025.1    36621   0.4649  0.72527  0.030796  0.087954   0.15598       OK         OK
   103  334.5  0.28  37409.6    66779   0.5602  0.74047  0.030195   0.11223   0.11711       OK         OK
   104  350.4  0.18  57646.7   109241   0.5277  0.71683  0.032782  0.083869   0.16652       OK         OK
   105   86.6  6.43  3783.79        4   988.25        0         0         0         1     FAIL         OK
   106    297  0.49  35362.2    55314   0.6393  0.74147  0.048556   0.11447  0.095504       OK         OK
   107  310.5  0.36  17534.4  37078.5   0.4729  0.71447  0.032394  0.089312   0.16382       OK         OK
   108  153.3  0.15  25065.8  32646.2   0.7678  0.71851  0.036285  0.090679   0.15453       OK         OK
   109  429.1  0.33  14412.6  19099.7   0.7546  0.13646  0.034902  0.095178   0.13346       OK       FAIL
   110   94.4  6.76  3580.76   3.6557  979.493        0         0         0         1       OK         OK
   111  398.1  0.39  6765.51    11985   0.5645  0.71577  0.038032  0.088439   0.15776       OK         OK
   112  431.2  0.44  41049.1  67592.8   0.6073  0.71978  0.057436  0.098354   0.12443       OK         OK
   113  207.4  0.14  19450.8  26619.4   0.7307  0.72923  0.056935  0.095976   0.11786       OK         OK
   114  192.4   0.5    10000  14188.5   0.7048  0.70236  0.033289    0.1051   0.15925       OK         OK
   115   83.6   4.8  2217.29   2.3043  962.223        0         0         0         1       OK         OK
   116  448.7  0.27  52342.9  55951.8   0.9355  0.70057  0.051622   0.10727   0.14054       OK         OK
   117  297.2  0.15  11135.4  14452.1   0.1705  0.72174  0.043612   0.11815    0.1165     FAIL         OK
   118    409  0.15  14825.9  21170.7   0.7003  0.74563  0.056116  0.091938   0.10632       OK         OK
   119  330.9  0.31  46938.1  89168.1   0.5264  0.72697  0.053359   0.10121   0.11846       OK         OK
   120     40  3.92  4680.94   4.8725  960.682        0         0         0         1       OK         OK

streams: 20   discarded values: 0
  density    pass  18   fail   2   no data   0
  fractions  pass  19   fail   1   no data   0
```
<!-- demo:end -->

`examples/synthetic_hmb.pdf` is a synthetic, image-only H&MB sheet (20 streams of flue gas and condensate).
`clean.tokens.json` is its real OCR output (Apple Vision, 200 dpi) — every stream matches the truth.
`faulty.tokens.json` is the same output with **injected faults that reproduce defects seen in real documents**:

| Injected fault | Result |
|---|---|
| Two cells read without a separator | split back into two cells, both values correct |
| Same, where the second cell starts with a digit | split correctly — a greedy exponent (`\d+`) would read `5.74E-025` instead of `5.74E-02`: in range, plausible, and 23 orders of magnitude wrong |
| Row label truncated by OCR (`Carbon Dioxide` → `Carbon`) | row still found: schema labels are the shortest distinguishing text |
| Volumetric flow printed with one significant figure | **density check fails** on that stream |
| Misread digit in a density | **density check fails** |
| Misread digit in a mass fraction | **fraction-sum check fails** |

The first three are repaired. The last three are exactly the streams the checks flag — and nothing else is flagged.

## Run it on your own sheet

```bash
pip install -e ".[ocr]"                       # Tesseract backend: Linux, Windows, macOS
hmb-extract run sheet.pdf --page 5 --schema my_schema.yaml -o sheet.json
```

On macOS, Apple Vision reads tables better. Build its helper once:

```bash
swiftc -O swift/ocr_tokens.swift -o build/ocr_tokens     # then --ocr vision (default on macOS)
```

Keep 200 dpi: Vision downsizes large images internally, so a higher dpi reads *worse*.

Every value in `sheet.json` keeps its provenance — the pixel box of the value, of its row label and of its column header — so any number can be traced back and checked by eye.

### Adapt the schema

Copy `examples/schema.yaml`. Each row has a `code`, a `label` (the shortest text that identifies the row — OCR may truncate the rest), a unit and a plausible range. Mass-fraction rows go under `components`.

## Check data from any extractor

The checks do not care where the numbers come from — OCR, an LLM reading a datasheet, or a spreadsheet:

```bash
hmb-extract check records.json --schema examples/schema.yaml    # exit code 1 if any stream fails
```

```json
{"streams": {"204": {"values": {"m": 2306.51, "V": "2,5271", "rho": 912.7,
                                "w_N2": 0.72, "w_O2": 0.05, "w_CO2": 0.10, "w_H2O": 0.13}}}}
```

Values may be numbers or text in BR (`2306,51`) or US (`2,306.51`) format. A missing value gives "no data", never "pass".

## Limits

- One sheet (page) per run.
- PDFs with a real text layer are out of scope for v1: use a text extractor, then `hmb-extract check`.
- Row/column association assumes labels on the left and stream IDs as column headers. A different layout degrades extraction — and the checks make that visible instead of silent.

## Development

```bash
pip install -e ".[dev]"
pytest -m "not ocr"
```

MIT License.

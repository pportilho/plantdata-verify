# Architecture

## Goal

`hmb-extract` converts scanned heat & material balance sheets into structured stream records while making uncertainty and inconsistency visible.

The design deliberately separates **extraction** from **verification**. OCR can be swapped without changing the engineering checks, and checks can be applied to records produced by sources other than OCR.

## Data flow

```text
PDF / image
   |
   v
rasterize (PDF only)
   |
   v
OCR backend
   |
   v
Token(text, confidence, bbox)
   |
   v
token cleanup / split repair
   |
   v
schema-anchored recomposition
   |
   +--> domain rejection -> discarded[]
   |
   v
StreamRecord(values + provenance)
   |
   v
physics checks
   |
   v
terminal table + JSON report
```

## Modules

| Module | Responsibility |
|---|---|
| `ocr/` | Rasterization and pluggable OCR backends |
| `tokens.py` | Token model, normalization and repair of malformed/colliding OCR tokens |
| `numbers.py` | Robust numeric parsing across BR/US/scientific formats |
| `schema.py` | Process schema, units, ranges, stream-header pattern and check configuration |
| `recompose.py` | Rebuild rows/columns into process streams using labels, headers and geometry |
| `checks.py` | Layout-independent engineering consistency checks |
| `report.py` | Machine-readable JSON plus human-readable table/summary |
| `cli.py` | `run` and `check` command surfaces |

## Key design decisions

### 1. The schema is an engineering contract

The schema is not just a parser configuration. It states what the document is expected to contain:

- row identity;
- engineering unit;
- plausible numeric range;
- stream-ID syntax;
- relationships that can be checked independently.

This prevents a visually plausible OCR token from silently becoming trusted process data.

### 2. Geometry is a hypothesis

Bounding boxes answer:

> Which row and stream is this value probably associated with?

They do not answer:

> Is this value physically believable?

`recompose.py` therefore uses geometry for association and the schema for acceptance.

### 3. Rejection is explicit

A value outside its row domain is placed in `discarded` with:

- raw OCR text;
- row;
- stream;
- bounding box;
- reason.

The tool does not silently coerce an impossible engineering value into a valid record.

### 4. Missing data never becomes PASS

Physics checks return one of:

- `pass`;
- `fail`;
- `no_data`.

A check cannot pass unless all required inputs exist and are numerically usable.

### 5. Verification is layout-independent

Density and fraction checks operate only on structured values. The same layer can therefore validate data produced by:

- the bundled OCR path;
- another OCR engine;
- an LLM extractor;
- a spreadsheet/parser;
- manually assembled JSON.

This is the main boundary that keeps the project extensible.

## Provenance

Each accepted cell stores bounding boxes for:

- the value itself;
- the matched row label;
- the stream header.

That supports a human verification workflow without pretending that automated checks eliminate review.

## Test strategy

The test suite covers four levels:

1. **unit:** numeric parsing, schema, checks and token repair;
2. **structural:** recomposition from token geometry;
3. **integration:** CLI/report behavior;
4. **end-to-end:** synthetic scanned H&MB -> real OCR tokens -> reconstructed truth.

OCR-dependent tests are marked separately because they require a local OCR engine.

## Security / privacy posture

The public repository contains synthetic engineering data only. CI includes a sanitization check intended to catch accidental leakage before publication.

The project should not ship customer drawings, plant data, proprietary process conditions or client identifiers as test fixtures.

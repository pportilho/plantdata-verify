# Validation strategy

## What is being validated?

The project distinguishes three different questions.

### 1. Did OCR read characters?

Measured by token output from the OCR backend.

This alone is insufficient.

### 2. Did the extractor reconstruct the intended process table?

Measured with the synthetic sheet:

- generated ground truth in `examples/truth.json`;
- image-only PDF in `examples/synthetic_hmb.pdf`;
- real OCR token output in `examples/clean.tokens.json`;
- end-to-end tests comparing the reconstructed streams to truth.

The included clean OCR fixture reconstructs all 20 synthetic streams.

### 3. Are extracted numbers internally consistent?

Measured independently from layout using engineering relationships.

Current checks:

#### Density

```text
rho_calculated = mass_flow / volumetric_flow
```

The configured relative tolerance determines pass/fail.

#### Mass fractions

```text
sum(component_mass_fractions) ~= 1
```

The configured absolute tolerance determines pass/fail.

## Controlled failure injection

`examples/faulty.tokens.json` contains deliberate defects that model failure modes seen in OCR/document extraction:

| Failure mode | Expected behavior |
|---|---|
| adjacent numeric cells merged | repair the split |
| exponent boundary merged with next cell | repair without accepting a plausible but wrong exponent |
| row label truncated | still identify it using the shortest distinguishing schema label |
| volumetric flow precision destroyed | density FAIL |
| density digit misread | density FAIL |
| component fraction digit misread | fractions FAIL |

The goal is not to maximize automatic repair. The goal is to repair defects that can be justified and **surface the rest**.

## What a PASS means

A PASS means:

> the values available for that configured relationship are internally consistent within tolerance.

It does **not** mean:

- the OCR is globally perfect;
- every table cell is correct;
- the process model itself is correct;
- the source document is authoritative;
- engineering review can be skipped.

## Why this matters

A conventional extraction benchmark compares output with a hand-labeled answer key. That is useful for development but does not help when a new client document has no answer key.

Physics checks supply a second signal that can run on previously unseen sheets.

That changes the operational question from:

> "Did the OCR return a number?"

to:

> "Did the system return a number that is traceable, in-domain and consistent with independent engineering relationships?"

## Current limits

The validation evidence is intentionally bounded:

- one synthetic H&MB layout;
- one real OCR token fixture from Apple Vision;
- Tesseract covered separately;
- two physics relationships;
- single-page extraction.

Future evidence should expand across layout families, scan quality levels, OCR backends and additional process relationships rather than presenting one synthetic benchmark as universal performance.

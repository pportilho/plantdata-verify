"""Command line: `hmb-extract run` and `hmb-extract check`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ocr
from .checks import FAIL, as_float, run_checks
from .recompose import recompose
from .report import build_report, format_table, summarize, write_json
from .schema import SchemaError, load_schema
from .tokens import load_tokens

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _load_input(path: Path, page: int, dpi: int, backend: str):
    suffix = path.suffix.lower()
    if suffix == ".json":
        tokens, meta = load_tokens(path)
        return tokens, {"file": path.name, **{k: v for k, v in meta.items() if k in ("width", "height")}}
    if suffix == ".pdf":
        image = ocr.rasterize(path, page=page, dpi=dpi)
    elif suffix in IMAGE_SUFFIXES:
        image = path
    else:
        raise ocr.OcrUnavailable(f"unsupported input {path.suffix!r}: use a PDF, an image or a tokens .json")
    tokens = ocr.get_backend(backend)(image)
    return tokens, {"file": path.name, "page": page if suffix == ".pdf" else None, "dpi": dpi, "ocr": backend}


def _print_summary(summary: dict, n_streams: int, n_discarded: int) -> None:
    print(f"streams: {n_streams}   discarded values: {n_discarded}")
    for name, s in summary.items():
        print(f"  {name:10} pass {s['pass']:3}   fail {s['fail']:3}   no data {s['no_data']:3}")


def cmd_run(args) -> int:
    schema = load_schema(args.schema)
    tokens, source = _load_input(Path(args.input), args.page, args.dpi, args.ocr)
    recomp = recompose(tokens, schema)
    if not recomp.streams:
        print(f"error: no stream header row found (pattern {schema.stream_header!r}, at least 5 stream IDs "
              f"on one line); {recomp.labels_found} row labels were recognised", file=sys.stderr)
        return 2
    checks = {sid: run_checks(rec.values(), schema) for sid, rec in recomp.streams.items()}
    report = build_report(recomp, checks, source)
    print(format_table({sid: rec.values() for sid, rec in recomp.streams.items()}, checks,
                       [r.code for r in schema.rows]))
    print()
    _print_summary(report["summary"], len(recomp.streams), len(recomp.discarded))
    if args.output:
        write_json(args.output, report)
        print(f"\nwrote {args.output}")
    return 0


def cmd_check(args) -> int:
    schema = load_schema(args.schema)
    data = json.loads(Path(args.records).read_text(encoding="utf-8"))
    streams = data.get("streams") if isinstance(data, dict) else None
    if not isinstance(streams, dict):
        print('error: expected {"streams": {"<id>": {"values": {"<code>": <number or text>}}}}', file=sys.stderr)
        return 2
    values = {sid: {code: as_float(v) for code, v in ((s or {}).get("values") or {}).items()}
              for sid, s in streams.items()}
    checks = {sid: run_checks(vals, schema) for sid, vals in values.items()}
    print(format_table(values, checks, [r.code for r in schema.rows]))
    print()
    summary = summarize(checks)
    _print_summary(summary, len(values), 0)
    return 1 if any(s[FAIL] for s in summary.values()) else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="hmb-extract",
        description="Extract H&MB tables from scanned engineering PDFs and verify every stream with physics.")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="extract from a PDF, an image or a tokens JSON, then check")
    run.add_argument("input")
    run.add_argument("--schema", required=True)
    run.add_argument("--page", type=int, default=1)
    run.add_argument("--dpi", type=int, default=200)
    run.add_argument("--ocr", default="auto", choices=["auto", "vision", "tesseract"])
    run.add_argument("-o", "--output")
    check = sub.add_parser("check", help="check records from any extractor (OCR, LLM, spreadsheet)")
    check.add_argument("records")
    check.add_argument("--schema", required=True)
    args = parser.parse_args(argv)
    try:
        return cmd_run(args) if args.command == "run" else cmd_check(args)
    except (SchemaError, ocr.OcrUnavailable, FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

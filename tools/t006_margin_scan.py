#!/usr/bin/env python
"""T006 (bounded analysis): can OCR recover the scan's margin canonical clues?

T005B recorded a real coverage gap: humanities canonical location clues (a
Stephanus reference such as ``605B``) had no mapping to this pipeline's
PDF-page hint. The 商务印书馆 1986 柏拉图《理想国》 facsimile prints Stephanus
page numbers and A–E section letters in the outer margin, so the same OCR pass
that makes the body searchable may also make that clue resolvable.

This script measures *only* that, and only with what the OCR cache already
contains:

* how many OCR lines are pure alphanumeric margin tokens;
* where a requested token (default ``605`` and ``607``, the case's clue) occurs;
* geometry of each hit, so the page can be verified visually.

It is a measurement, not a product feature: the result is reported with the
page images for verification and is not treated as confirmed evidence.

No model or API call is made.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import t006_ocr_evidence as oe  # noqa: E402

DEFAULT_CACHE = oe.DEFAULT_CACHE_DIR
DEFAULT_OUT = REPO_ROOT / "data/private/T006-01/margin_scan"
TOKEN_RE = re.compile(r"^[A-Za-z0-9]{1,4}$")


def line_box_px(line: dict) -> list[float] | None:
    quad = line.get("box")
    if not quad:
        return None
    xs = [float(point[0]) for point in quad]
    ys = [float(point[1]) for point in quad]
    return [min(xs), min(ys), max(xs), max(ys)]


def scan(pages: dict[int, dict], targets: list[str]) -> dict:
    body_lines: list[list[float]] = []
    token_lines: list[dict] = []
    text_lines = 0

    for page_number in sorted(pages):
        for line in pages[page_number]["lines"]:
            text = (line.get("text") or "").strip()
            if not text:
                continue
            text_lines += 1
            box = line_box_px(line)
            if TOKEN_RE.match(text) and len(text) <= 4:
                token_lines.append(
                    {
                        "pdf_page": page_number,
                        "token": text,
                        "box_px": box,
                        "line_index": line["line_index"],
                    }
                )
            elif len(text) >= 8 and box:
                body_lines.append(box)

    column_left = statistics.median([box[0] for box in body_lines]) if body_lines else 0.0
    column_right = statistics.median([box[2] for box in body_lines]) if body_lines else 0.0

    # tokens outside the body column, or noticeably to its right
    margin_tokens = [
        token
        for token in token_lines
        if token["box_px"]
        and (
            token["box_px"][2] < column_left - 2
            or token["box_px"][0] > column_right + 2
        )
    ]
    stephanus_numbers = [
        token for token in margin_tokens if token["token"].isdigit()
        and len(token["token"]) == 3
    ]
    section_letters = [
        token
        for token in margin_tokens
        if len(token["token"]) == 1 and token["token"].isalpha()
    ]

    hits: list[dict] = []
    for page_number in sorted(pages):
        joined = pages[page_number]["joined_text"]
        for target in targets:
            if target in joined:
                offsets = [
                    index
                    for index in range(len(joined))
                    if joined.startswith(target, index)
                ]
                token_hit = any(
                    token["pdf_page"] == page_number and token["token"] == target
                    for token in token_lines
                )
                hits.append(
                    {
                        "pdf_page": page_number,
                        "target": target,
                        "occurrences": len(offsets),
                        "as_standalone_line": token_hit,
                    }
                )

    numeric_values = sorted({int(t["token"]) for t in stephanus_numbers})
    return {
        "result_version": "t006-margin-scan-v1",
        "pages_scanned": len(pages),
        "text_lines": text_lines,
        "body_column_px": [round(column_left, 1), round(column_right, 1)],
        "standalone_token_lines": len(token_lines),
        "margin_token_lines": len(margin_tokens),
        "margin_stephanus_like_numbers": len(stephanus_numbers),
        "margin_section_letters": len(section_letters),
        "numeric_range": [min(numeric_values), max(numeric_values)] if numeric_values else None,
        "targets": targets,
        "target_hits": hits,
        "model_calls": 0,
        "cost_usd": 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ocr-cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--targets", nargs="*", default=["605", "607"])
    args = parser.parse_args(argv)

    started = time.perf_counter()
    pages = oe.load_cached_pages(args.ocr_cache)
    if not pages:
        print(json.dumps({"error": f"no OCR cache at {args.ocr_cache}"}, indent=2))
        return 2
    report = scan(pages, args.targets)
    report["seconds"] = round(time.perf_counter() - started, 2)
    report["ocr_cache"] = oe.repo_relative(args.ocr_cache)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "margin_scan.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

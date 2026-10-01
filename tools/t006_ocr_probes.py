#!/usr/bin/env python
"""T006 zero-cost regression probes for the experimental OCR evidence path.

These probes need **no OCR engine run**: they use the already-cached OCR pages
plus the real scan. They exist so the new adapter can be re-verified cheaply
after any change, and so the honest-failure statuses stay covered:

1. ``coordinate_round_trip``   — PageToDevice -> DeviceToPage returns the input
   point, i.e. the OCR pixel->PDF-point conversion used for highlight geometry
   is the exact inverse of the T003 renderer transform;
2. ``ocr_cache_integrity``     — every cached page carries text and boxes, and
   no page beyond the document is present;
3. ``ocr_line_locates``        — a passage taken verbatim from a cached page's
   OCR text localizes to exactly that page with ``complete_match`` and
   ``geometry_ok``;
4. ``no_cache_page_needs_ocr`` — a page with no OCR cache entry reports
   ``needs_ocr`` instead of inventing geometry;
5. ``repeated_text_ambiguous`` — text occurring twice in the same window is
   reported ``ambiguous`` with no geometry (no guessed highlight).

Outputs are aggregates only; private source text is never printed.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import pypdfium2 as pdfium  # noqa: E402
from pypdfium2 import raw as pdfium_raw  # noqa: E402

import t003_evidence_localize as ev  # noqa: E402
import t006_ocr_evidence as oe  # noqa: E402

DEFAULT_PDF = REPO_ROOT / "data/private/T005B-01/source/T005B-01_source.pdf"
DEFAULT_CACHE = oe.DEFAULT_CACHE_DIR
DEFAULT_OUT = REPO_ROOT / "data/private/T006-01/probes"


def probe_coordinate_round_trip(pdf_path: Path) -> dict:
    document = pdfium.PdfDocument(str(pdf_path))
    try:
        page = document[0]
        try:
            width_pt, height_pt = page.get_size()
            scale = 144.0 / 72.0
            device_w = int(width_pt * scale)
            device_h = int(height_pt * scale)
            worst = 0.0
            checked = 0
            for fx, fy in ((0.1, 0.1), (0.5, 0.5), (0.9, 0.2), (0.25, 0.8)):
                page_x, page_y = fx * width_pt, fy * height_pt
                device_x = ctypes.c_int(0)
                device_y = ctypes.c_int(0)
                ok = pdfium_raw.FPDF_PageToDevice(
                    page.raw, 0, 0, device_w, device_h, 0,
                    page_x, page_y, ctypes.byref(device_x), ctypes.byref(device_y),
                )
                if not ok:
                    continue
                back_x = ctypes.c_double(0.0)
                back_y = ctypes.c_double(0.0)
                ok = pdfium_raw.FPDF_DeviceToPage(
                    page.raw, 0, 0, device_w, device_h, 0,
                    device_x.value, device_y.value,
                    ctypes.byref(back_x), ctypes.byref(back_y),
                )
                if not ok:
                    continue
                checked += 1
                worst = max(
                    worst, abs(back_x.value - page_x), abs(back_y.value - page_y)
                )
        finally:
            page.close()
    finally:
        document.close()
    return {
        "name": "coordinate_round_trip",
        "passed": checked == 4 and worst < 0.5,
        "detail": f"checked={checked} worst_error_pt={round(worst, 4)}",
    }


def probe_cache_integrity(pdf_path: Path, cache_dir: Path) -> dict:
    pages = oe.load_cached_pages(cache_dir)
    document = pdfium.PdfDocument(str(pdf_path))
    try:
        page_count = len(document)
    finally:
        document.close()

    missing_boxes = 0
    empty_pages = 0
    out_of_range = 0
    for page_number, record in pages.items():
        if not 1 <= page_number <= page_count:
            out_of_range += 1
        if not record.get("lines"):
            empty_pages += 1
            continue
        for line in record["lines"]:
            if line.get("text") and not line.get("box"):
                missing_boxes += 1
    return {
        "name": "ocr_cache_integrity",
        "passed": bool(pages)
        and out_of_range == 0
        and missing_boxes == 0
        and empty_pages == 0,
        "detail": (
            f"cached_pages={len(pages)}/{page_count} empty_pages={empty_pages} "
            f"lines_without_box={missing_boxes} out_of_range={out_of_range}"
        ),
    }


def probe_line_locates(pdf_path: Path, pages: dict[int, dict]) -> dict:
    page_number = max(pages)  # any cached page; the passage is taken from itself
    record = pages[page_number]
    long_lines = [line["text"] for line in record["lines"] if len(line["text"]) >= 20]
    if not long_lines:
        return {
            "name": "ocr_line_locates",
            "passed": False,
            "detail": "no long line available in the cached sample",
        }
    passage = long_lines[0]
    source = oe.OcrEvidenceSource(pdf_path, pages, dpi=144.0)
    try:
        outcome = source.locate(passage, (page_number, page_number), radius=0)
    finally:
        source.close()
    pages_hit = [f["page_number"] for f in outcome.get("fragments", [])]
    return {
        "name": "ocr_line_locates",
        "passed": (
            outcome["status"] == "located"
            and pages_hit == [page_number]
            and outcome.get("complete_match") is True
            and outcome["missing_box_chars"] == 0
            and outcome["invalid_box_chars"] == 0
        ),
        "detail": (
            f"status={outcome['status']} pages={pages_hit} "
            f"complete={outcome.get('complete_match')} "
            f"missing_boxes={outcome['missing_box_chars']} "
            f"invalid_boxes={outcome['invalid_box_chars']} "
            f"query_chars={outcome['norm_query_chars']}"
        ),
    }


def probe_missing_page_needs_ocr(pdf_path: Path, pages: dict[int, dict]) -> dict:
    # Simulate a page that OCR could not read: drop one page from the cache for
    # this probe only, so the honest-failure path stays covered even when the
    # real cache is complete.
    absent = next((p for p in range(1, 460) if p not in pages), 1)
    subset = {p: record for p, record in pages.items() if p != absent}
    source = oe.OcrEvidenceSource(pdf_path, subset, dpi=144.0)
    try:
        outcome = source.locate("这是一个不可能出现在扫描页上的测试字符串", (absent, absent), radius=0)
    finally:
        source.close()
    return {
        "name": "no_cache_page_needs_ocr",
        "passed": outcome["status"] == "needs_ocr" and not outcome["fragments"],
        "detail": f"status={outcome['status']} fragments={len(outcome['fragments'])}",
    }


def probe_repeated_text_ambiguous(pdf_path: Path, pages: dict[int, dict]) -> dict:
    page_number = max(pages)
    text = pages[page_number]["joined_text"]
    compact = "".join(char for char in text if not char.isspace())
    # Use a string that really occurs twice in the OCR page text rather than
    # fabricating duplicates: count n-gram repeats inside the page text.
    counts: dict[str, int] = {}
    for size in (8, 6, 4):
        for start in range(0, len(compact) - size + 1):
            counts[compact[start : start + size]] = (
                counts.get(compact[start : start + size], 0) + 1
            )
    repeated = next((n for n, c in counts.items() if c >= 2), None)
    if repeated is None:
        return {
            "name": "repeated_text_ambiguous",
            "passed": False,
            "detail": "no repeated n-gram available in the cached page",
        }
    source = oe.OcrEvidenceSource(pdf_path, pages, dpi=144.0)
    try:
        outcome = source.locate(repeated, (page_number, page_number), radius=0)
    finally:
        source.close()
    return {
        "name": "repeated_text_ambiguous",
        "passed": outcome["status"] == "ambiguous" and not outcome["fragments"],
        "detail": (
            f"status={outcome['status']} occurrences={outcome['occurrences_in_hint_window']} "
            f"fragments={len(outcome['fragments'])}"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--ocr-cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    started = time.perf_counter()
    pages = oe.load_cached_pages(args.ocr_cache)
    if not pages:
        print(json.dumps({"error": f"no OCR cache at {args.ocr_cache}"}, indent=2))
        return 2

    probes = [
        probe_coordinate_round_trip(args.pdf),
        probe_cache_integrity(args.pdf, args.ocr_cache),
        probe_line_locates(args.pdf, pages),
        probe_missing_page_needs_ocr(args.pdf, pages),
        probe_repeated_text_ambiguous(args.pdf, pages),
    ]
    passed = sum(1 for probe in probes if probe["passed"])
    summary = {
        "result_version": "t006-probes-v1",
        "cached_pages": len(pages),
        "probes_total": len(probes),
        "probes_passed": passed,
        "seconds": round(time.perf_counter() - started, 2),
        "model_calls": 0,
        "cost_usd": 0.0,
        "probes": probes,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "t006_probe_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for probe in probes:
        mark = "PASS" if probe["passed"] else "FAIL"
        print(f"{mark}  {probe['name']:<28} {probe['detail']}")
    print(f"{passed}/{len(probes)} probes passed; report: {args.out_dir}")
    return 0 if passed == len(probes) else 1


if __name__ == "__main__":
    raise SystemExit(main())

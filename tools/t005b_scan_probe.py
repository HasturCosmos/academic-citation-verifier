#!/usr/bin/env python
"""T005B zero-cost source probe: is a candidate PDF searchable at all?

The T005B case starts from a real secondary-source passage plus a candidate
primary-source PDF. Before any retrieval or model call, this probe answers the
only question that decides whether the current product path can proceed:
does the candidate PDF carry a usable text layer?

It reports aggregates and page-level counts only. It never prints private page
text, and it writes its machine-readable output under ``data/private/``.

No model or API call is made anywhere in this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

import pypdfium2 as pdfium

REPO_ROOT = Path(__file__).resolve().parents[1]

# Mirrors tools/t003_evidence_localize.py: a page holding fewer normalized
# characters than this is treated as having no usable text layer.
MIN_TEXT_LAYER_CHARS = 20

# Invisible formatting characters; removing them cannot change what a reader
# sees, so it cannot turn an unsearchable page into a searchable one.
INVISIBLE_CHARS = frozenset("\u00ad\u200b\u200c\u200d\ufeff")


def normalize_len(text: str) -> int:
    return sum(1 for char in text if not char.isspace() and char not in INVISIBLE_CHARS)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scan(pdf_path: Path) -> dict:
    started = time.perf_counter()
    document = pdfium.PdfDocument(str(pdf_path))
    try:
        page_count = len(document)
        char_counts: list[int] = []
        for index in range(page_count):
            page = document[index]
            try:
                textpage = page.get_textpage()
                try:
                    char_counts.append(normalize_len(textpage.get_text_range()))
                finally:
                    textpage.close()
            finally:
                page.close()
    finally:
        document.close()

    searchable = [count for count in char_counts if count >= MIN_TEXT_LAYER_CHARS]
    return {
        "page_count": page_count,
        "pages_with_usable_text_layer": len(searchable),
        "pages_without_usable_text_layer": page_count - len(searchable),
        "total_normalized_chars": sum(char_counts),
        "max_page_chars": max(char_counts) if char_counts else 0,
        "median_page_chars": (
            int(statistics.median(char_counts)) if char_counts else 0
        ),
        "per_page_char_counts": char_counts,
        "scan_seconds": round(time.perf_counter() - started, 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--render-pages",
        type=int,
        nargs="*",
        default=None,
        help="1-based page numbers to render as PNG for visual inspection",
    )
    parser.add_argument("--render-dir", type=Path, default=None)
    parser.add_argument("--render-dpi", type=float, default=120.0)
    args = parser.parse_args(argv)

    if not args.pdf.exists():
        print(f"missing PDF: {args.pdf}", file=sys.stderr)
        return 2

    report = {
        "pdf": str(args.pdf),
        "pdf_bytes": args.pdf.stat().st_size,
        "pdf_sha256": sha256_of(args.pdf),
        "text_layer_min_chars": MIN_TEXT_LAYER_CHARS,
    }
    report.update(scan(args.pdf))

    if args.render_pages:
        render_dir = args.render_dir or args.pdf.parent / "rendered_pages"
        render_dir.mkdir(parents=True, exist_ok=True)
        document = pdfium.PdfDocument(str(args.pdf))
        try:
            scale = args.render_dpi / 72.0
            rendered = []
            for page_number in args.render_pages:
                index = page_number - 1
                if not 0 <= index < len(document):
                    continue
                page = document[index]
                try:
                    image = page.render(scale=scale).to_pil()
                finally:
                    page.close()
                target = render_dir / f"page_{page_number:04d}.png"
                image.save(target)
                rendered.append(str(target))
        finally:
            document.close()
        report["rendered_pages"] = rendered

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    public = {
        key: value
        for key, value in report.items()
        if key not in ("per_page_char_counts", "rendered_pages")
    }
    if report.get("rendered_pages"):
        public["rendered_page_count"] = len(report["rendered_pages"])
    public["text_layer_verdict"] = (
        "searchable" if report["pages_with_usable_text_layer"] else "needs_ocr"
    )
    print(json.dumps(public, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

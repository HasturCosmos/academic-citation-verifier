#!/usr/bin/env python
"""T006 Phase 2: bounded OCR benchmark over a frozen sample of the T005B-01 scan.

Design rules taken from ``ops/OVERNIGHT_GOAL_2026-10-01.md`` and the T006 brief:

* the sample is frozen *before* any engine runs (``--freeze`` writes the page
  list, the rendered-page sha256 values and the extracted sample PDF);
* only the two Phase-1 shortlisted candidates are benchmarked
  (OCRmyPDF, RapidOCR) and neither is allowed to be the other's ground truth;
* the secondary paraphrase is never used as primary-source truth;
* page provenance is carried explicitly: every recognised line keeps its
  PDF page index, so the existing T003 localization contract can be fed;
* full recognised text is written only under ``data/private/``; stdout stays
  aggregate-only so private source text never leaks into logs.

No model/API call is made by this file. Everything is local inference.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Frozen before any engine ran: the T005B-identified front-matter pages plus
# representative body pages chosen by visual inspection of the scan.
#   p1  book cover / title area
#   p3  colophon (the page the publisher metadata was read from in T005B)
#   p10 译者引言 last page (already rendered and identified by T005B)
#   p30 第一卷 body text, printed page 19
#   p200 第五卷 body text, printed page 189
#   p420 第十卷 body text, printed page 409 (the Book X region the case is about)
DEFAULT_SAMPLE_PAGES = [1, 3, 10, 30, 200, 420]
DEFAULT_DPI = 300.0


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_relative(path: Path | str) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# --------------------------------------------------------------------------
# sample freezing
# --------------------------------------------------------------------------


def freeze_sample(
    pdf_path: Path, pages: list[int], dpi: float, out_dir: Path
) -> dict:
    """Render the fixed pages and extract the fixed sample PDF (no OCR)."""
    import pypdfium2 as pdfium

    pages_dir = out_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    document = pdfium.PdfDocument(str(pdf_path))
    rendered: list[dict] = []
    try:
        scale = dpi / 72.0
        for page_number in pages:
            index = page_number - 1
            if not 0 <= index < len(document):
                raise SystemExit(f"page {page_number} outside 1..{len(document)}")
            page = document[index]
            try:
                image = page.render(scale=scale).to_pil()
                width, height = page.get_size()
            finally:
                page.close()
            target = pages_dir / f"p{page_number:04d}_{int(dpi)}dpi.png"
            image.save(target)
            rendered.append(
                {
                    "pdf_page": page_number,
                    "png": repo_relative(target),
                    "png_sha256": sha256_of(target),
                    "png_bytes": target.stat().st_size,
                    "pixel_size": [image.width, image.height],
                    "pdf_point_size": [round(width, 2), round(height, 2)],
                    "render_dpi": dpi,
                }
            )
    finally:
        document.close()

    sample_pdf = out_dir / "sample.pdf"
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for page_number in pages:
        writer.add_page(reader.pages[page_number - 1])
    with sample_pdf.open("wb") as handle:
        writer.write(handle)

    manifest = {
        "result_version": "t006-sample-v1",
        "source_pdf": repo_relative(pdf_path),
        "source_pdf_sha256": sha256_of(pdf_path),
        "source_page_count": len(reader.pages),
        "sample_pages_pdf_1_based": pages,
        "render_dpi": dpi,
        "sample_pdf": repo_relative(sample_pdf),
        "sample_pdf_sha256": sha256_of(sample_pdf),
        "rendered_pages": rendered,
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (out_dir / "sample_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


# --------------------------------------------------------------------------
# engine: RapidOCR
# --------------------------------------------------------------------------


def _to_plain(value):
    """RapidOCR returns numpy arrays; make them JSON-serialisable."""
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            return value.tolist()
    except Exception:  # noqa: BLE001
        pass
    return value


def load_engine(engine_name: str = "rapidocr", params: dict | None = None):
    """Construct one OCR engine instance (model load is the expensive part)."""
    if engine_name != "rapidocr":
        raise ValueError(f"unsupported engine: {engine_name}")
    from rapidocr import RapidOCR

    return RapidOCR(params=params or None)


def recognize(engine, image_path: Path) -> dict:
    """Run one recognition pass and return a JSON-serialisable page record."""
    call_started = time.perf_counter()
    result = engine(str(image_path))
    seconds = round(time.perf_counter() - call_started, 2)

    raw_texts = getattr(result, "txts", None) if result is not None else None
    raw_scores = getattr(result, "scores", None) if result is not None else None
    raw_boxes = getattr(result, "boxes", None) if result is not None else None
    texts = list(raw_texts) if raw_texts is not None else []
    scores = [float(s) for s in raw_scores] if raw_scores is not None else []
    boxes = [_to_plain(b) for b in raw_boxes] if raw_boxes is not None else []

    lines = [
        {
            "line_index": index,
            "text": text,
            "score": round(scores[index], 4) if index < len(scores) else None,
            "box": boxes[index] if index < len(boxes) else None,
        }
        for index, text in enumerate(texts)
    ]
    return {
        "seconds": seconds,
        "line_count": len(lines),
        "char_count": sum(len(line["text"]) for line in lines),
        "joined_text": "\n".join(texts),
        "lines": lines,
    }


def run_rapidocr(pages: list[dict], out_dir: Path, engine_params: dict) -> dict:
    engine_dir = out_dir / "rapidocr"
    engine_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    engine = load_engine("rapidocr", engine_params)
    load_seconds = round(time.perf_counter() - started, 2)

    page_records: list[dict] = []
    for entry in pages:
        png = REPO_ROOT / entry["png"]
        measured = recognize(engine, png)
        record = {
            "pdf_page": entry["pdf_page"],
            "png": entry["png"],
            **measured,
        }
        page_records.append(record)
        (engine_dir / f"p{entry['pdf_page']:04d}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"  page {entry['pdf_page']:>3}: lines={record['line_count']:>3} "
            f"chars={record['char_count']:>4} seconds={record['seconds']}",
            flush=True,
        )

    summary = {
        "result_version": "t006-run-v1",
        "engine": "rapidocr",
        "engine_params": engine_params or "defaults",
        "model_load_seconds": load_seconds,
        "total_seconds": round(sum(p["seconds"] for p in page_records), 2),
        "pages": [
            {
                "pdf_page": p["pdf_page"],
                "line_count": p["line_count"],
                "char_count": p["char_count"],
                "seconds": p["seconds"],
            }
            for p in page_records
        ],
        "model_calls": 0,
        "cost_usd": 0.0,
        "outputs_dir": repo_relative(engine_dir),
    }
    (engine_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


ENGINES = {"rapidocr": run_rapidocr}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--pages",
        type=int,
        nargs="*",
        default=DEFAULT_SAMPLE_PAGES,
        help="1-based PDF page numbers of the frozen sample",
    )
    parser.add_argument("--dpi", type=float, default=DEFAULT_DPI)
    parser.add_argument("--freeze", action="store_true", help="render + manifest only")
    parser.add_argument("--engine", choices=sorted(ENGINES), default=None)
    parser.add_argument("--params", type=Path, default=None, help="JSON engine params")
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out_dir / "sample_manifest.json"

    if args.freeze or not manifest_path.exists():
        manifest = freeze_sample(args.pdf, args.pages, args.dpi, args.out_dir)
        print(
            json.dumps(
                {
                    "frozen": True,
                    "sample_pages": manifest["sample_pages_pdf_1_based"],
                    "render_dpi": manifest["render_dpi"],
                    "sample_pdf": manifest["sample_pdf"],
                    "sample_pdf_sha256": manifest["sample_pdf_sha256"],
                    "rendered_pages": len(manifest["rendered_pages"]),
                },
                indent=2,
            )
        )
        if args.freeze:
            return 0

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.engine is None:
        print("no --engine given; sample frozen only", file=sys.stderr)
        return 0

    params = (
        json.loads(args.params.read_text(encoding="utf-8")) if args.params else {}
    )
    print(f"engine={args.engine} pages={manifest['sample_pages_pdf_1_based']}")
    summary = ENGINES[args.engine](manifest["rendered_pages"], args.out_dir, params)
    print(
        json.dumps(
            {
                "engine": summary["engine"],
                "model_load_seconds": summary["model_load_seconds"],
                "total_seconds": summary["total_seconds"],
                "per_page": summary["pages"],
                "outputs_dir": summary["outputs_dir"],
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

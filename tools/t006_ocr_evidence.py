#!/usr/bin/env python
"""T006 Phase 2 (experimental): RapidOCR-backed evidence source.

This is the *thinnest* possible bridge between the OCR engine chosen in
``ops/T006_OCR_REUSE_REPORT.md`` and the proven T003 evidence layer.

Instead of rewriting localization, this module subclasses
``t003_evidence_localize.PdfEvidenceSource`` and replaces exactly three things:

* ``page_text``       — the page's text comes from OCR instead of a PDF text layer;
* ``page_entries``    — per-character entries + boxes are interpolated inside the
  OCR line quadrilaterals and converted back from OCR pixels to PDF points;
* ``page_has_text_layer`` — a page counts as searchable when OCR produced text.

Everything downstream is unchanged and shared: hint-window search, unique-match /
ambiguity rule, cross-page fragment splitting, per-line highlight runs, render
diagnostics and ``geometry_ok``.

Experimental status: this adapter is deliberately *not* part of the default
product path. It is only used when the user asks for scan/OCR ingestion, and it
still requires page-image verification before OCR text can be treated as
evidence. No OCR engine is bundled or auto-installed.

No model/API call is made by this file.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import pypdfium2 as pdfium  # noqa: E402
from pypdfium2 import raw as pdfium_raw  # noqa: E402
from pypdfium2.internal import RotationToConst  # noqa: E402

import t003_evidence_localize as ev  # noqa: E402
import t006_ocr_benchmark as bench  # noqa: E402

DEFAULT_OCR_DPI = 300.0
DEFAULT_CACHE_DIR = REPO_ROOT / "data/private/T006-01/ocr/rapidocr"


def repo_relative(path: Path | str) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# --------------------------------------------------------------------------- #
# resumable document OCR
# --------------------------------------------------------------------------- #


def render_page_png(document, page_number: int, dpi: float, target: Path) -> dict:
    page = document[page_number - 1]
    try:
        image = page.render(scale=dpi / 72.0).to_pil()
        width, height = page.get_size()
    finally:
        page.close()
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return {
        "pixel_size": [image.width, image.height],
        "pdf_point_size": [round(width, 2), round(height, 2)],
        "render_dpi": dpi,
    }


def ocr_document(
    pdf_path: Path,
    *,
    pages: list[int] | None = None,
    dpi: float = DEFAULT_OCR_DPI,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    engine_name: str = "rapidocr",
    params: dict | None = None,
    quiet: bool = False,
) -> dict[int, dict]:
    """OCR the requested pages, caching each page so the run is resumable.

    Returns ``{pdf_page_number: page_record}``. A page record always carries
    ``lines`` (text + pixel-space quadrilateral) and ``render_dpi``.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    images_dir = cache_dir / "images"
    document = pdfium.PdfDocument(str(pdf_path))
    engine = None
    records: dict[int, dict] = {}
    started = time.perf_counter()
    try:
        page_count = len(document)
        todo = list(range(1, page_count + 1)) if pages is None else list(pages)
        for position, page_number in enumerate(todo, start=1):
            cache_path = cache_dir / f"p{page_number:04d}.json"
            if cache_path.exists():
                records[page_number] = json.loads(
                    cache_path.read_text(encoding="utf-8")
                )
                continue
            if engine is None:
                engine = bench.load_engine(engine_name, params)
            png = images_dir / f"p{page_number:04d}_{int(dpi)}dpi.png"
            if not png.exists():
                render_page_png(document, page_number, dpi, png)
            measured = bench.recognize(engine, png)
            record = {
                "pdf_page": page_number,
                "engine": engine_name,
                "engine_params": params or "defaults",
                "png": repo_relative(png),
                "pixel_size": [int(v) for v in _png_size(png)],
                "pdf_point_size": [
                    round(value, 2)
                    for value in _page_display_size(document, page_number)
                ],
                "render_dpi": dpi,
                **measured,
            }
            cache_path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            records[page_number] = record
            if not quiet:
                elapsed = time.perf_counter() - started
                print(
                    f"  [{position}/{len(todo)}] page {page_number:>4}: "
                    f"lines={record['line_count']:>3} "
                    f"chars={record['char_count']:>4} "
                    f"{record['seconds']}s (elapsed {elapsed:.0f}s)",
                    flush=True,
                )
    finally:
        document.close()
    return records


def _png_size(path: Path) -> tuple[int, int]:
    from PIL import Image

    with Image.open(path) as image:
        return image.size


def _page_display_size(document, page_number: int) -> tuple[float, float]:
    page = document[page_number - 1]
    try:
        return page.get_size()
    finally:
        page.close()


def load_cached_pages(cache_dir: Path) -> dict[int, dict]:
    pages: dict[int, dict] = {}
    if not cache_dir.exists():
        return pages
    for path in sorted(cache_dir.glob("p*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        pages[int(record["pdf_page"])] = record
    return pages


# --------------------------------------------------------------------------- #
# OCR-backed evidence source
# --------------------------------------------------------------------------- #


class OcrEvidenceSource(ev.PdfEvidenceSource):
    """T003 evidence source whose text and character boxes come from OCR."""

    def __init__(
        self,
        pdf_path: Path,
        ocr_pages: dict[int, dict],
        dpi: float = ev.DEFAULT_DPI,
    ) -> None:
        super().__init__(pdf_path, dpi=dpi)
        self.ocr_pages = ocr_pages
        self._device_cache: dict[int, tuple[int, int]] = {}

    # -- text --------------------------------------------------------------- #

    def page_text(self, index: int) -> str:
        record = self.ocr_pages.get(index + 1)
        return record["joined_text"] if record else ""

    def page_has_text_layer(self, index: int) -> bool:
        record = self.ocr_pages.get(index + 1)
        if not record:
            return False
        return record["char_count"] >= ev.MIN_TEXT_LAYER_CHARS

    # -- geometry ----------------------------------------------------------- #

    def _device_size_at(self, page, dpi: float) -> tuple[int, int]:
        width, height = page.get_size()
        scale = dpi / 72.0
        return math.ceil(width * scale), math.ceil(height * scale)

    def _device_to_page(
        self,
        page,
        device_size: tuple[int, int],
        points: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        """Inverse of ``PdfEvidenceSource._to_device`` (pixels -> PDF points)."""
        width, height = device_size
        rotation = RotationToConst[0]
        page_points: list[tuple[float, float]] = []
        for device_x, device_y in points:
            page_x = ctypes.c_double(0.0)
            page_y = ctypes.c_double(0.0)
            ok = pdfium_raw.FPDF_DeviceToPage(
                page.raw, 0, 0, width, height, rotation,
                int(round(device_x)), int(round(device_y)),
                ctypes.byref(page_x), ctypes.byref(page_y),
            )
            if not ok:
                raise RuntimeError(
                    f"FPDF_DeviceToPage failed for point ({device_x}, {device_y})"
                )
            page_points.append((float(page_x.value), float(page_y.value)))
        return page_points

    def page_entries(self, index: int) -> tuple[list[str], list[tuple | None]]:
        if index in self._entries_cache:
            return self._entries_cache[index]
        record = self.ocr_pages.get(index + 1)
        entries: list[str] = []
        boxes: list[tuple[float, float, float, float] | None] = []
        if record:
            ocr_dpi = float(record.get("render_dpi") or DEFAULT_OCR_DPI)
            page = self.document[index]
            try:
                device_size = self._device_size_at(page, ocr_dpi)
                for line in record["lines"]:
                    text = line.get("text") or ""
                    quad = line.get("box")
                    if not text:
                        continue
                    char_boxes: list[tuple[float, float, float, float] | None] = []
                    for position in range(len(text)):
                        if not quad:
                            char_boxes.append(None)
                            continue
                        xs = [float(point[0]) for point in quad]
                        ys = [float(point[1]) for point in quad]
                        left, right = min(xs), max(xs)
                        top, bottom = min(ys), max(ys)
                        step = (right - left) / len(text)
                        x0 = left + position * step
                        x1 = x0 + step
                        char_boxes.append((x0, top, x1, bottom))
                    # one FPDF_DeviceToPage batch per line keeps the ctypes
                    # overhead proportional to line count, not character count
                    corners: list[tuple[float, float]] = []
                    for box in char_boxes:
                        if box is None:
                            continue
                        x0, top, x1, bottom = box
                        corners.extend(
                            [(x0, top), (x1, top), (x0, bottom), (x1, bottom)]
                        )
                    mapped = (
                        self._device_to_page(page, device_size, corners)
                        if corners
                        else []
                    )
                    cursor = 0
                    for character, box in zip(text, char_boxes):
                        entries.append(character)
                        if box is None:
                            boxes.append(None)
                            continue
                        quad_points = mapped[cursor : cursor + 4]
                        cursor += 4
                        page_xs = [point[0] for point in quad_points]
                        page_ys = [point[1] for point in quad_points]
                        entry_box = (
                            min(page_xs),
                            min(page_ys),
                            max(page_xs),
                            max(page_ys),
                        )
                        boxes.append(entry_box)
            finally:
                page.close()
        self._entries_cache[index] = (entries, boxes)
        return entries, boxes


def ocr_text_index(
    ocr_pages: dict[int, dict], min_chars: int = ev.MIN_TEXT_LAYER_CHARS
) -> list[dict]:
    """Page-level documents for retrieval, in reading (page) order."""
    documents: list[dict] = []
    for page_number in sorted(ocr_pages):
        record = ocr_pages[page_number]
        if record["char_count"] < min_chars:
            continue
        documents.append(
            {
                "pdf_page": page_number,
                "page_label": f"scan pages {page_number}-{page_number}",
                "text": record["joined_text"],
                "char_count": record["char_count"],
            }
        )
    return documents


# --------------------------------------------------------------------------- #
# CLI: OCR a page range into the resumable cache
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--pages-start", type=int, default=None)
    parser.add_argument("--pages-end", type=int, default=None)
    parser.add_argument("--dpi", type=float, default=DEFAULT_OCR_DPI)
    parser.add_argument("--engine", default="rapidocr")
    parser.add_argument("--params", type=Path, default=None)
    args = parser.parse_args(argv)

    pages = None
    if args.pages_start or args.pages_end:
        start = args.pages_start or 1
        end = args.pages_end or 10 ** 9
        document = pdfium.PdfDocument(str(args.pdf))
        try:
            end = min(end, len(document))
        finally:
            document.close()
        pages = list(range(start, end + 1))

    params = (
        json.loads(args.params.read_text(encoding="utf-8")) if args.params else None
    )
    started = time.perf_counter()
    records = ocr_document(
        args.pdf,
        pages=pages,
        dpi=args.dpi,
        cache_dir=args.cache_dir,
        engine_name=args.engine,
        params=params,
    )
    total_chars = sum(record["char_count"] for record in records.values())
    empty_pages = sum(
        1 for record in records.values() if record["char_count"] < ev.MIN_TEXT_LAYER_CHARS
    )
    print(
        json.dumps(
            {
                "engine": args.engine,
                "pages_ocr": len(records),
                "pages_without_text": empty_pages,
                "total_chars": total_chars,
                "dpi": args.dpi,
                "wall_seconds": round(time.perf_counter() - started, 1),
                "cache_dir": repo_relative(args.cache_dir),
                "outputs": "private (data/private is git-ignored)",
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

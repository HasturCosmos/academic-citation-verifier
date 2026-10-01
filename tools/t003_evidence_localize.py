#!/usr/bin/env python
"""T003 evidence localization: saved PaperQA2 candidate -> page geometry -> highlight.

This is the thin, retrieval-independent evidence layer required by
``ops/T003_C04_HIGHLIGHT_EXPERIMENT.md``. It consumes artifacts that already
exist (the saved T001 candidate list and the original C04 PDF) and produces:

    candidate text + page hint -> exact PDF page(s) + character boxes
                               -> original page render + highlighted render
                               -> machine-readable evidence record

Contract points taken from the T003 brief and the T002 architecture plan:

* normalization removes whitespace only (plus invisible format characters such
  as soft hyphen / zero-width space) and keeps a mapping back to the original
  character positions;
* digits, annotations and CJK characters are never deleted to force a match;
* a unique full match is ``located``; zero matches is ``unmatched``; several
  matches is ``ambiguous``; a hinted page without a usable text layer is
  ``needs_ocr`` (OCR itself is out of scope for T003);
* only a unique full match may emit a highlight -- no guessed geometry;
* cross-page candidates are split into one fragment per PDF page;
* PDF-native coordinates, CropBox and rotation are preserved in the record and
  converted to image pixels with the same scale PDFium uses for rendering;
* highlights use per-character boxes grouped into text runs, never one large
  rectangle over unrelated body text;
* private text/images are only written under ``data/private/``.

No model or API call is made anywhere in this file.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import re
import statistics
import sys
import time
from pathlib import Path

import pypdfium2 as pdfium
from pypdfium2 import raw as pdfium_raw
from pypdfium2.internal import RotationToConst
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = REPO_ROOT / "data/private/C04/pqa_corpus/C04.pdf"
DEFAULT_RESULTS = REPO_ROOT / "data/private/C04/results/m1e1_c04_20261001-113927.json"
DEFAULT_OUT_DIR = REPO_ROOT / "data/private/C04/evidence"
DEFAULT_DPI = 144.0

PAGE_LABEL_RE = re.compile(r"pages?\s+(\d+)\s*-\s*(\d+)", re.IGNORECASE)

# Invisible formatting characters: removing them cannot change what a reader
# sees, and PDF text layers insert them for line-breaking / de-hyphenation.
INVISIBLE_CHARS = frozenset("\u00ad\u200b\u200c\u200d\ufeff")

# A page with fewer normalized characters than this is treated as having no
# usable text layer (scanned image page).
MIN_TEXT_LAYER_CHARS = 20


# --------------------------------------------------------------------------- #
# text normalization
# --------------------------------------------------------------------------- #


def normalize_text(text: str) -> tuple[str, list[int]]:
    """Return whitespace-free text plus a normalized->original index mapping."""
    kept: list[str] = []
    mapping: list[int] = []
    for index, char in enumerate(text):
        if char.isspace() or char in INVISIBLE_CHARS:
            continue
        kept.append(char)
        mapping.append(index)
    return "".join(kept), mapping


def normalize_entries(entries: list[str]) -> tuple[str, list[int]]:
    """Like :func:`normalize_text` but over per-character entries.

    ``entries`` may contain multi-character strings (surrogate handling in the
    PDFium text API), so the returned mapping is per normalized character.
    """
    parts: list[str] = []
    pos_to_entry: list[int] = []
    for entry_index, entry in enumerate(entries):
        if not entry:
            continue
        if entry.isspace() or entry in INVISIBLE_CHARS:
            continue
        parts.append(entry)
        pos_to_entry.extend([entry_index] * len(entry))
    return "".join(parts), pos_to_entry


def parse_page_hint(page_label: str | None) -> tuple[int, int] | None:
    """Parse a PaperQA2 page label such as ``Rejoice2026 pages 109-109``."""
    if not page_label:
        return None
    match = PAGE_LABEL_RE.search(page_label)
    if not match:
        return None
    first, last = int(match.group(1)), int(match.group(2))
    return (first, last) if first <= last else (last, first)


def find_all(haystack: str, needle: str) -> list[int]:
    """All (overlapping) start offsets of ``needle`` in ``haystack``."""
    if not needle:
        return []
    offsets: list[int] = []
    start = haystack.find(needle)
    while start != -1:
        offsets.append(start)
        start = haystack.find(needle, start + 1)
    return offsets


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------- #
# PDFium source
# --------------------------------------------------------------------------- #


def _charbox(textpage, index: int) -> tuple[float, float, float, float] | None:
    """Tight character box in PDF points, falling back to the loose box."""
    for loose in (False, True):
        try:
            box = textpage.get_charbox(index, loose=loose)
        except Exception:  # noqa: BLE001 - PDFium raises several error types
            continue
        if box is None:
            continue
        left, bottom, right, top = (float(value) for value in box)
        if right < left:
            left, right = right, left
        if top < bottom:
            bottom, top = top, bottom
        if right == left or top == bottom:
            continue
        return (left, bottom, right, top)
    return None


class PdfEvidenceSource:
    """PDFium-backed page text, character geometry and page rendering."""

    def __init__(self, pdf_path: Path, dpi: float = DEFAULT_DPI) -> None:
        self.path = Path(pdf_path)
        self.dpi = float(dpi)
        self.scale = self.dpi / 72.0
        self.document = pdfium.PdfDocument(str(self.path))
        self.page_count = len(self.document)
        self._norm_cache: dict[int, str] = {}
        self._entries_cache: dict[int, tuple[list[str], list[tuple | None]]] = {}
        self._meta_cache: dict[int, dict] = {}

    def close(self) -> None:
        self.document.close()

    # -- page metadata ----------------------------------------------------- #

    def page_meta(self, index: int) -> dict:
        if index in self._meta_cache:
            return self._meta_cache[index]
        page = self.document[index]
        try:
            width, height = page.get_size()
            meta = {
                "page_index": index,
                "page_number": index + 1,
                "rotation": int(page.get_rotation()),
                "display_size_pt": [float(width), float(height)],
            }
            for name in ("get_mediabox", "get_cropbox"):
                getter = getattr(page, name, None)
                if getter is None:
                    continue
                try:
                    box = getter()
                except Exception:  # noqa: BLE001
                    box = None
                if box is not None:
                    meta[name.removeprefix("get_")] = [float(value) for value in box]
        finally:
            page.close()
        self._meta_cache[index] = meta
        return meta

    # -- text -------------------------------------------------------------- #

    def page_text(self, index: int) -> str:
        page = self.document[index]
        try:
            textpage = page.get_textpage()
            try:
                return textpage.get_text_range()
            finally:
                textpage.close()
        finally:
            page.close()

    def norm_page(self, index: int) -> str:
        if index not in self._norm_cache:
            self._norm_cache[index] = normalize_text(self.page_text(index))[0]
        return self._norm_cache[index]

    def page_has_text_layer(self, index: int) -> bool:
        return len(self.norm_page(index)) >= MIN_TEXT_LAYER_CHARS

    def page_entries(self, index: int) -> tuple[list[str], list[tuple | None]]:
        """Per-character entries and their PDF-point boxes for one page."""
        if index in self._entries_cache:
            return self._entries_cache[index]
        page = self.document[index]
        try:
            textpage = page.get_textpage()
            try:
                count = textpage.count_chars()
                entries = [textpage.get_text_range(i, 1) for i in range(count)]
                boxes = [_charbox(textpage, i) for i in range(count)]
            finally:
                textpage.close()
        finally:
            page.close()
        self._entries_cache[index] = (entries, boxes)
        return entries, boxes

    # -- search ------------------------------------------------------------ #

    def _region(self, pages: list[int]) -> tuple[str, list[tuple[int, int, int]]]:
        parts: list[str] = []
        segments: list[tuple[int, int, int]] = []
        cursor = 0
        for page_index in pages:
            text = self.norm_page(page_index)
            segments.append((cursor, cursor + len(text), page_index))
            parts.append(text)
            cursor += len(text)
        return "".join(parts), segments

    @staticmethod
    def _map_span(
        segments: list[tuple[int, int, int]], start: int, end: int
    ) -> list[tuple[int, int, int]]:
        fragments: list[tuple[int, int, int]] = []
        for seg_start, seg_end, page_index in segments:
            overlap_start = max(start, seg_start)
            overlap_end = min(end, seg_end)
            if overlap_start < overlap_end:
                fragments.append(
                    (page_index, overlap_start - seg_start, overlap_end - seg_start)
                )
        return fragments

    def locate(
        self,
        candidate_text: str,
        page_hint: tuple[int, int] | None,
        radius: int = 1,
    ) -> dict:
        """Locate a candidate passage using the hint window, then the PDF."""
        query = normalize_text(candidate_text)[0]
        result: dict = {
            "norm_query_chars": len(query),
            "hint_pages": list(page_hint) if page_hint else None,
            "hint_confirmed": False,
            "search_scope": "hint_window",
            "occurrences_in_hint_window": 0,
            "occurrences_in_pdf": None,
            "scan_seconds": 0.0,
            "status": "unmatched",
            "fragments": [],
            "invalid_box_chars": 0,
            "missing_box_chars": 0,
        }
        started = time.perf_counter()

        if page_hint is None:
            window = list(range(self.page_count))
            result["search_scope"] = "whole_pdf"
        else:
            low = max(0, page_hint[0] - 1 - radius)
            high = min(self.page_count - 1, page_hint[1] - 1 + radius)
            window = list(range(low, high + 1))

        region, segments = self._region(window)
        starts = find_all(region, query)
        result["occurrences_in_hint_window"] = len(starts)
        result["scanned_pages"] = len(window)

        if len(starts) == 1:
            result["status"] = "located"
            result["hint_confirmed"] = page_hint is not None
            fragments = self._map_span(segments, starts[0], starts[0] + len(query))
            result["occurrences_in_pdf"] = self._count_in_pdf(query)
        elif len(starts) > 1:
            result["status"] = "ambiguous"
            result["ambiguous_offsets"] = starts[:50]
            fragments = []
        else:
            fragments = []
            if page_hint is not None:
                # The stored page range is a fallible hint: fall back to the
                # whole document before declaring the candidate unmatched.
                full_region, full_segments = self._region(list(range(self.page_count)))
                full_starts = find_all(full_region, query)
                result["search_scope"] = "whole_pdf"
                result["occurrences_in_pdf"] = len(full_starts)
                result["scanned_pages"] = self.page_count
                if len(full_starts) == 1:
                    result["status"] = "located"
                    result["hint_confirmed"] = False
                    fragments = self._map_span(
                        full_segments, full_starts[0], full_starts[0] + len(query)
                    )
                elif len(full_starts) > 1:
                    result["status"] = "ambiguous"
                    result["ambiguous_offsets"] = full_starts[:50]
            if result["status"] == "unmatched" and page_hint is not None:
                hint_window_has_text = any(
                    self.page_has_text_layer(p - 1)
                    for p in range(page_hint[0], page_hint[1] + 1)
                    if 0 <= p - 1 < self.page_count
                )
                if not hint_window_has_text:
                    result["status"] = "needs_ocr"

        result["scan_seconds"] = round(time.perf_counter() - started, 3)

        if result["status"] == "located":
            result["fragments"] = [
                self._build_fragment(page_index, norm_start, norm_end)
                for page_index, norm_start, norm_end in fragments
            ]
            result["invalid_box_chars"] = sum(
                fragment["invalid_box_chars"] for fragment in result["fragments"]
            )
            result["missing_box_chars"] = sum(
                fragment["missing_box_chars"] for fragment in result["fragments"]
            )
            located_chars = sum(
                fragment["norm_char_count"] for fragment in result["fragments"]
            )
            result["located_norm_chars"] = located_chars
            result["complete_match"] = located_chars == len(query)
        return result

    def _count_in_pdf(self, query: str) -> int:
        region, _ = self._region(list(range(self.page_count)))
        return len(find_all(region, query))

    # -- geometry ---------------------------------------------------------- #

    def device_size(self, page_index: int) -> tuple[int, int]:
        """Rendered bitmap size in pixels, computed exactly as ``render`` does."""
        page = self.document[page_index]
        try:
            return self._device_size_for(page)
        finally:
            page.close()

    def _device_size_for(self, page) -> tuple[int, int]:
        """Bitmap size PDFium produces for ``page.render(scale=self.scale)``.

        ``get_size()`` is already rotation-aware (it reports the displayed page
        size), and pypdfium2 only swaps the axes for *additional* rotation
        requested by the caller. Rendering here never adds rotation, so the
        device size is simply the display size times the scale factor.
        """
        width, height = page.get_size()
        return math.ceil(width * self.scale), math.ceil(height * self.scale)

    def _to_device(
        self, page, device_size: tuple[int, int], points: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        """Page space -> bitmap pixels using PDFium's own renderer transform.

        The ``rotate`` argument mirrors ``PdfPage.render``: PDFium applies the
        page's own /Rotate internally, so only *additional* rotation would be
        passed here, and this adapter never adds any.
        """
        rotation = RotationToConst[0]
        width, height = device_size
        device_points: list[tuple[float, float]] = []
        for page_x, page_y in points:
            device_x = ctypes.c_int(0)
            device_y = ctypes.c_int(0)
            ok = pdfium_raw.FPDF_PageToDevice(
                page.raw, 0, 0, width, height, rotation,
                float(page_x), float(page_y),
                ctypes.byref(device_x), ctypes.byref(device_y),
            )
            if not ok:
                raise RuntimeError(
                    f"FPDF_PageToDevice failed for point ({page_x}, {page_y})"
                )
            device_points.append((float(device_x.value), float(device_y.value)))
        return device_points

    def _build_fragment(self, page_index: int, norm_start: int, norm_end: int) -> dict:
        entries, boxes = self.page_entries(page_index)
        _, pos_to_entry = normalize_entries(entries)
        entry_indices = pos_to_entry[norm_start:norm_end]
        taken = [(entries[i], boxes[i]) for i in sorted(set(entry_indices))]

        meta = self.page_meta(page_index)
        page = self.document[page_index]
        try:
            device_size = self._device_size_for(page)
            char_boxes: list[dict] = []
            missing = 0
            invalid = 0
            for entry, box in taken:
                if box is None:
                    missing += 1
                    continue
                corners = [
                    (box[0], box[1]),
                    (box[2], box[1]),
                    (box[0], box[3]),
                    (box[2], box[3]),
                ]
                device = self._to_device(page, device_size, corners)
                xs = [point[0] for point in device]
                ys = [point[1] for point in device]
                rect = [min(xs), min(ys), max(xs), max(ys)]
                if rect[2] <= rect[0] or rect[3] <= rect[1]:
                    invalid += 1
                    continue
                char_boxes.append(
                    {
                        "char": entry,
                        "box_pt": [round(value, 3) for value in box],
                        "box_px": [round(value, 2) for value in rect],
                    }
                )
        finally:
            page.close()

        # Runs are grouped in pixel space so that rotated pages (whose text
        # lines are not horizontal in page space) still group per visual line.
        runs = group_runs([entry["box_px"] for entry in char_boxes])

        return {
            "page_index": page_index,
            "page_number": page_index + 1,
            "norm_char_count": norm_end - norm_start,
            "first_norm_char": norm_start,
            "last_norm_char": norm_end - 1,
            "char_count_with_box": len(char_boxes),
            "missing_box_chars": missing,
            "invalid_box_chars": invalid,
            "highlight_run_count": len(runs),
            "page_meta": meta,
            "coordinate_system": {
                "pdf_points": "PDF page space (MediaBox-relative, y up) as "
                "returned by FPDFText_GetCharBox",
                "pixels": "top-left origin, y down, produced by "
                "FPDF_PageToDevice with the same start/size/rotate "
                "arguments as FPDF_RenderPageBitmap, so crop and rotation "
                "are handled by PDFium rather than by an assumed y-flip",
                "dpi": self.dpi,
                "scale": self.scale,
                "device_size_px": list(device_size),
            },
            "char_boxes": char_boxes,
            "highlight_boxes": [
                {"box_px": [round(value, 2) for value in box]} for box in runs
            ],
        }

    def render_page(self, page_index: int) -> Image.Image:
        page = self.document[page_index]
        try:
            bitmap = page.render(scale=self.scale)
            try:
                return bitmap.to_pil().convert("RGB")
            finally:
                bitmap.close()
        finally:
            page.close()


def median_char_width(boxes: list[list[float]]) -> float:
    widths = [max(box[2] - box[0], 0.01) for box in boxes]
    return statistics.median(widths) if widths else 1.0


def group_runs(boxes: list[list[float]]) -> list[list[float]]:
    """Group pixel-space character boxes into one rectangle per visual line.

    Boxes are ``[left, top, right, bottom]`` with ``top``/``bottom`` following
    the image convention (y grows downward).

    Line assignment compares each box against the running centre of a line, not
    against the line's accumulated extent: the latter grows with every merged
    row and would eventually swallow the whole text block.
    """
    if not boxes:
        return []
    median_width = median_char_width(boxes)
    lines: list[list[list[float]]] = []
    for box in sorted(boxes, key=lambda b: (0.5 * (b[1] + b[3]), b[0])):
        box_center = 0.5 * (box[1] + box[3])
        box_height = max(box[3] - box[1], 0.01)
        for line in lines:
            line_centers = [0.5 * (item[1] + item[3]) for item in line]
            line_heights = [max(item[3] - item[1], 0.01) for item in line]
            center = statistics.median(line_centers)
            tolerance = 0.6 * max(box_height, statistics.median(line_heights))
            if abs(box_center - center) <= tolerance:
                line.append(box)
                break
        else:
            lines.append([box])

    runs: list[list[float]] = []
    for line in lines:
        line.sort(key=lambda b: b[0])
        current = list(line[0])
        for box in line[1:]:
            gap = box[0] - current[2]
            if gap > max(1.5 * median_width, 0.6 * (current[3] - current[1])):
                runs.append(current)
                current = list(box)
            else:
                current[0] = min(current[0], box[0])
                current[1] = min(current[1], box[1])
                current[2] = max(current[2], box[2])
                current[3] = max(current[3], box[3])
        runs.append(current)
    runs.sort(key=lambda b: (b[1], b[0]))
    return runs


# --------------------------------------------------------------------------- #
# highlight rendering
# --------------------------------------------------------------------------- #


def draw_highlights(
    image: Image.Image,
    runs_px: list[list[float]],
    label: str,
    page_number: int,
) -> tuple[Image.Image, dict]:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    clipped = 0
    for box in runs_px:
        x0, y0, x1, y1 = box
        pad_x = 2.0
        pad_y = max(1.0, (y1 - y0) * 0.12)
        rect = [
            max(0.0, x0 - pad_x),
            max(0.0, y0 - pad_y),
            min(float(width), x1 + pad_x),
            min(float(height), y1 + pad_y),
        ]
        if rect[2] <= rect[0] or rect[3] <= rect[1]:
            clipped += 1
            continue
        if rect[0] > 0.0 or rect[1] > 0.0 or rect[2] < width or rect[3] < height:
            pass
        draw.rectangle(rect, fill=(255, 214, 0, 92), outline=(214, 108, 0, 230), width=2)

    highlighted = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    label_draw = ImageDraw.Draw(highlighted)
    try:
        font = ImageFont.load_default(size=max(12, int(0.011 * width)))
    except TypeError:  # pragma: no cover - very old Pillow
        font = ImageFont.load_default()
    text = f"{label}  |  PDF page {page_number}  |  {len(runs_px)} highlight run(s)"
    text_draw = ImageDraw.Draw(highlighted)
    text_draw.rectangle([4, 4, 4 + 9 * len(text), 4 + 22], fill=(255, 255, 255))
    text_draw.text((8, 8), text, fill=(150, 30, 0), font=font)
    stats = {
        "highlight_run_count": len(runs_px),
        "clipped_runs": clipped,
        "highlight_area_fraction": round(
            sum(
                max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
                for box in runs_px
            )
            / float(width * height),
            5,
        ),
    }
    return highlighted, stats


def ink_ratio(image: Image.Image, box_px: list[float]) -> float:
    """Fraction of dark pixels inside a pixel box (geometry sanity signal)."""
    width, height = image.size
    x0 = max(0, int(box_px[0]))
    y0 = max(0, int(box_px[1]))
    x1 = min(width, int(round(box_px[2])))
    y1 = min(height, int(round(box_px[3])))
    if x1 <= x0 or y1 <= y0:
        return 0.0
    crop = image.crop((x0, y0, x1, y1)).convert("L")
    histogram = crop.histogram()
    total = sum(histogram)
    if not total:
        return 0.0
    dark = sum(histogram[:128])
    return dark / total


def finalize_fragment(
    fragment: dict, page_image: Image.Image, stats: dict, ink_ratios: list[float]
) -> None:
    """Attach render/geometry diagnostics and decide ``geometry_ok``."""
    expected = fragment["coordinate_system"]["device_size_px"]
    size_ok = list(page_image.size) == [int(value) for value in expected]
    fragment["render_stats"] = stats
    fragment["ink_ratios"] = ink_ratios
    fragment["render_size_matches_device"] = size_ok
    fragment["geometry_ok"] = bool(
        size_ok
        and stats["clipped_runs"] == 0
        and stats["highlight_area_fraction"] < 0.35
        and ink_ratios
        and all(ratio > 0.005 for ratio in ink_ratios)
    )


# --------------------------------------------------------------------------- #
# experiment driver
# --------------------------------------------------------------------------- #


def load_candidates(results_path: Path) -> list[dict]:
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    candidates = []
    for context in payload.get("contexts", []):
        rank = int(context.get("rank", 0))
        candidates.append(
            {
                "candidate_id": f"rank-{rank:02d}",
                "rank": rank,
                "score": context.get("score"),
                "page_label": context.get("page_label"),
                "text": context.get("text", ""),
            }
        )
    candidates.sort(key=lambda item: item["rank"])
    return candidates


def run(
    pdf_path: Path,
    results_path: Path,
    out_dir: Path,
    dpi: float,
    radius: int,
    only: list[str] | None = None,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates = load_candidates(results_path)
    if only:
        candidates = [c for c in candidates if c["candidate_id"] in only]

    fingerprints = {
        "pdf": {"path": str(pdf_path), "sha256": sha256_of(pdf_path),
                "bytes": pdf_path.stat().st_size},
        "results": {"path": str(results_path), "sha256": sha256_of(results_path),
                    "bytes": results_path.stat().st_size},
    }

    source = PdfEvidenceSource(pdf_path, dpi=dpi)
    records: list[dict] = []
    started = time.perf_counter()
    try:
        for candidate in candidates:
            hint = parse_page_hint(candidate["page_label"])
            outcome = source.locate(candidate["text"], hint, radius=radius)
            record = {
                "candidate_id": candidate["candidate_id"],
                "rank": candidate["rank"],
                "retrieval_score": candidate["score"],
                "source_page_label": candidate["page_label"],
                "candidate_chars": len(candidate["text"]),
                "source_text_path": str(out_dir / "private_candidate_texts.json"),
                **outcome,
                "artifacts": [],
                "visual_review": None,
            }
            if outcome["status"] == "located":
                for fragment in outcome["fragments"]:
                    page_number = fragment["page_number"]
                    page_image = source.render_page(fragment["page_index"])
                    base = f"{candidate['candidate_id']}_pdf{page_number:04d}"
                    original_path = out_dir / f"{base}_original.png"
                    highlight_path = out_dir / f"{base}_highlight.png"
                    page_image.save(original_path)
                    highlighted, stats = draw_highlights(
                        page_image,
                        [
                            item["box_px"]
                            for item in fragment["highlight_boxes"]
                        ],
                        candidate["candidate_id"],
                        page_number,
                    )
                    highlighted.save(highlight_path)
                    fragment["image"] = {
                        "original": str(original_path),
                        "highlight": str(highlight_path),
                        "pixel_size": list(page_image.size),
                        "dpi": dpi,
                    }
                    finalize_fragment(
                        fragment,
                        page_image,
                        stats,
                        [
                            round(ink_ratio(page_image, item["box_px"]), 4)
                            for item in fragment["highlight_boxes"]
                        ],
                    )
                    record["artifacts"].append(str(highlight_path))
            records.append(record)
            print(
                f"[{record['candidate_id']}] status={outcome['status']} "
                f"hint={outcome['hint_pages']} scope={outcome['search_scope']} "
                f"fragments={len(outcome['fragments'])} "
                f"located_chars={outcome.get('located_norm_chars', 0)}/"
                f"{outcome['norm_query_chars']} "
                f"missing_boxes={outcome['missing_box_chars']} "
                f"invalid_boxes={outcome['invalid_box_chars']} "
                f"scan={outcome['scan_seconds']}s",
                flush=True,
            )
    finally:
        source.close()

    # keep the raw candidate text in the private directory only
    (out_dir / "private_candidate_texts.json").write_text(
        json.dumps(
            {
                candidate["candidate_id"]: {
                    "page_label": candidate["page_label"],
                    "text": candidate["text"],
                }
                for candidate in candidates
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    elapsed = round(time.perf_counter() - started, 2)
    statuses: dict[str, int] = {}
    for record in records:
        statuses[record["status"]] = statuses.get(record["status"], 0) + 1

    summary = {
        "run_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "dpi": dpi,
        "search_radius": radius,
        "elapsed_seconds": elapsed,
        "candidate_count": len(records),
        "status_counts": statuses,
        "api_calls": 0,
        "api_cost_usd": 0.0,
        "fingerprints": fingerprints,
        "pages_scanned": sum(record.get("scanned_pages", 0) for record in records),
        "located_pages": sorted(
            {
                fragment["page_number"]
                for record in records
                for fragment in record["fragments"]
            }
        ),
        "geometry_ok": {
            record["candidate_id"]: all(
                fragment.get("geometry_ok", False) for fragment in record["fragments"]
            )
            for record in records
        },
        "records": records,
    }
    (out_dir / "evidence_records.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dpi", type=float, default=DEFAULT_DPI)
    parser.add_argument("--radius", type=int, default=1,
                        help="extra pages searched around the stored page hint")
    parser.add_argument("--only", nargs="*", default=None,
                        help="restrict to these candidate ids, e.g. rank-05")
    args = parser.parse_args(argv)

    summary = run(
        pdf_path=args.pdf,
        results_path=args.results,
        out_dir=args.out_dir,
        dpi=args.dpi,
        radius=args.radius,
        only=args.only,
    )
    print(json.dumps(
        {
            key: summary[key]
            for key in (
                "run_at",
                "candidate_count",
                "status_counts",
                "elapsed_seconds",
                "located_pages",
                "geometry_ok",
                "api_calls",
                "api_cost_usd",
            )
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""T003 regression probes for the evidence-localization layer.

Covers the scenarios required by ``ops/T003_C04_HIGHLIGHT_EXPERIMENT.md``:

* whitespace and line-wrap differences;
* repeated text -> ``ambiguous``;
* absent text -> ``unmatched``;
* cross-page candidates -> one fragment per page;
* rotated and cropped pages;
* a page without a usable text layer -> ``needs_ocr``;
* a wrong stored page hint -> whole-PDF fallback with ``hint_confirmed=False``.

The synthetic fixtures are generated at runtime by this script (plain
Latin-1 text and vector shapes). They contain no private material; only the
hint-fallback probe reuses a stored C04 candidate, and it prints aggregates
only. No model or API call is made.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import t003_evidence_localize as ev  # noqa: E402

REPO_ROOT = ev.REPO_ROOT
DEFAULT_OUT = REPO_ROOT / "data/private/C04/evidence/probes"


# --------------------------------------------------------------------------- #
# minimal synthetic PDF writer (Latin-1 base-14 text, no dependencies)
# --------------------------------------------------------------------------- #


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _content_stream(
    lines: list[str],
    font_size: float,
    leading: float,
    origin: tuple[float, float],
    draw_only: bool,
) -> str:
    if draw_only:
        # vector shapes only: no text layer at all
        return "0.1 0.2 0.7 RG 4 w 120 200 360 400 re S"
    parts = [
        "BT",
        f"/F1 {font_size} Tf",
        f"{leading} TL",
        f"1 0 0 1 {origin[0]} {origin[1]} Tm",
    ]
    for line in lines:
        parts.append(f"({_escape(line)}) Tj")
        parts.append("T*")
    parts.append("ET")
    return "\n".join(parts)


def build_pdf(
    pages: list[list[str]],
    *,
    rotate: int = 0,
    mediabox: tuple[float, float, float, float] = (0.0, 0.0, 612.0, 792.0),
    cropbox: tuple[float, float, float, float] | None = None,
    font_size: float = 16.0,
    leading: float = 24.0,
    origin: tuple[float, float] = (72.0, 700.0),
    draw_only: bool = False,
) -> bytes:
    page_count = len(pages)
    page_nums = [4 + index for index in range(page_count)]
    content_nums = [4 + page_count + index for index in range(page_count)]

    objects: dict[int, bytes] = {}
    kids = " ".join(f"{num} 0 R" for num in page_nums)
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode()
    objects[3] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica"
        b" /Encoding /WinAnsiEncoding >>"
    )
    for index, lines in enumerate(pages):
        extras = ""
        if cropbox is not None:
            extras += " /CropBox [%s]" % " ".join(str(value) for value in cropbox)
        if rotate:
            extras += f" /Rotate {rotate}"
        objects[page_nums[index]] = (
            f"<< /Type /Page /Parent 2 0 R"
            f" /MediaBox [{mediabox[0]} {mediabox[1]} {mediabox[2]} {mediabox[3]}]"
            f"{extras} /Resources << /Font << /F1 3 0 R >> >>"
            f" /Contents {content_nums[index]} 0 R >>"
        ).encode("latin-1")
        stream = _content_stream(lines, font_size, leading, origin, draw_only).encode(
            "latin-1"
        )
        objects[content_nums[index]] = (
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += f"{number} 0 obj\n".encode("latin-1") + objects[number] + b"\nendobj\n"

    highest = max(objects)
    xref_offset = len(out)
    out += f"xref\n0 {highest + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for number in range(1, highest + 1):
        out += b"%010d 00000 n \n" % offsets[number]
    out += (
        f"trailer\n<< /Size {highest + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(out)


# --------------------------------------------------------------------------- #
# probe helpers
# --------------------------------------------------------------------------- #


def locate(
    pdf_path: Path,
    text: str,
    hint: tuple[int, int] | None,
    out_dir: Path,
    identity: str,
) -> dict:
    """Run one localization plus highlighting, mirroring the main driver."""
    source = ev.PdfEvidenceSource(pdf_path, dpi=144.0)
    try:
        outcome = source.locate(text, hint)
        outcome["artifacts"] = []
        outcome["fragment_details"] = []
        if outcome["status"] == "located":
            for fragment in outcome["fragments"]:
                page_number = fragment["page_number"]
                page_image = source.render_page(fragment["page_index"])
                target = out_dir / f"{identity}_pdf{page_number:04d}_highlight.png"
                highlighted, stats = ev.draw_highlights(
                    page_image,
                    [item["box_px"] for item in fragment["highlight_boxes"]],
                    identity,
                    page_number,
                )
                highlighted.save(target)
                ink = [
                    round(ev.ink_ratio(page_image, item["box_px"]), 4)
                    for item in fragment["highlight_boxes"]
                ]
                meta = fragment["page_meta"]
                ev.finalize_fragment(fragment, page_image, stats, ink)
                outcome["artifacts"].append(str(target))
                outcome["fragment_details"].append(
                    {
                        "page_number": page_number,
                        "rotation": meta["rotation"],
                        "display_size_pt": meta["display_size_pt"],
                        "highlight_run_count": stats["highlight_run_count"],
                        "ink_ratio_min": min(ink),
                        "render_size_matches_device": fragment[
                            "render_size_matches_device"
                        ],
                        "geometry_ok": fragment["geometry_ok"],
                    }
                )
        outcome["page_count"] = source.page_count
        return outcome
    finally:
        source.close()


def naive_yflip_ink(pdf_path: Path, text: str, hint: tuple[int, int] | None) -> float:
    """Ink ratio if boxes were naively flipped against the *MediaBox* height.

    Reported next to the PDFium result so the rotated-page probe can show that
    the implemented convention is the one that actually lands on glyphs.
    """
    source = ev.PdfEvidenceSource(pdf_path, dpi=144.0)
    try:
        outcome = source.locate(text, hint)
        if outcome["status"] != "located":
            return 0.0
        fragment = outcome["fragments"][0]
        page_image = source.render_page(fragment["page_index"])
        media = fragment["page_meta"].get("mediabox") or [0.0, 0.0, 612.0, 792.0]
        media_height = media[3] - media[1]
        scale = source.scale
        ratios = []
        for item in fragment["char_boxes"]:
            x0, y0, x1, y1 = item["box_pt"]
            ratios.append(
                ev.ink_ratio(
                    page_image,
                    [x0 * scale, (media_height - y1) * scale,
                     x1 * scale, (media_height - y0) * scale],
                )
            )
        return round(min(ratios), 4) if ratios else 0.0
    finally:
        source.close()


def record(probes: list[dict], name: str, expectation: str, outcome: dict, **extra) -> None:
    probes.append(
        {
            "probe": name,
            "expectation": expectation,
            "status": outcome["status"],
            "search_scope": outcome["search_scope"],
            "hint_confirmed": outcome["hint_confirmed"],
            "fragments": len(outcome["fragments"]),
            "pages": [f["page_number"] for f in outcome["fragments"]],
            "artifacts": len(outcome["artifacts"]),
            "fragment_details": outcome["fragment_details"],
            **extra,
        }
    )


def pages_of(outcome: dict) -> list[int]:
    return [fragment["page_number"] for fragment in outcome["fragments"]]


# --------------------------------------------------------------------------- #
# probes
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--results",
        type=Path,
        default=ev.DEFAULT_RESULTS,
        help="stored T001 candidate list, used by the whitespace and hint probes",
    )
    parser.add_argument("--pdf", type=Path, default=ev.DEFAULT_PDF)
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    fixtures = args.out_dir / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)

    probes: list[dict] = []

    # --- 1. whitespace / line-wrap on a synthetic fixture ------------------ #
    sentence = "Alpha beta gamma delta epsilon zeta."
    wrap_pdf = fixtures / "synthetic_wrap.pdf"
    wrap_pdf.write_bytes(
        build_pdf([["Alpha beta gamma", "delta epsilon zeta."]])
    )
    variants = {
        "exact": sentence,
        "whitespace_stripped": sentence.replace(" ", ""),
        "newlines_and_tabs": "Alpha\nbeta\tgamma   delta\n\nepsilon zeta.",
        "padded": "   " + sentence + "   ",
    }
    for name, query in variants.items():
        outcome = locate(wrap_pdf, query, (1, 1), args.out_dir, f"wrap_{name}")
        ok = outcome["status"] == "located" and outcome["fragments"][0]["page_number"] == 1
        record(probes, f"whitespace/{name}", "located on page 1", outcome, ok=ok)

    # --- 2. repeated text -> ambiguous ------------------------------------ #
    repeated_pdf = fixtures / "synthetic_repeated.pdf"
    repeated_pdf.write_bytes(
        build_pdf(
            [
                [
                    "Repeated phrase appears here.",
                    "Unrelated filler line in between.",
                    "Repeated phrase appears here.",
                ]
            ]
        )
    )
    outcome = locate(
        repeated_pdf, "Repeated phrase appears here.", (1, 1), args.out_dir, "repeated"
    )
    record(
        probes,
        "repeated_text",
        "ambiguous, no highlight",
        outcome,
        ok=outcome["status"] == "ambiguous" and not outcome["artifacts"],
        occurrences=outcome["occurrences_in_hint_window"],
    )

    # --- 3. missing text -> unmatched ------------------------------------- #
    outcome = locate(
        repeated_pdf,
        "This sentence does not occur anywhere in the document.",
        (1, 1),
        args.out_dir,
        "missing",
    )
    record(
        probes,
        "missing_text",
        "unmatched, no highlight",
        outcome,
        ok=outcome["status"] == "unmatched" and not outcome["artifacts"],
    )

    # --- 4. cross-page candidate ------------------------------------------ #
    head = "The first half of the sentence runs to the end of page one and"
    tail = "the second half continues at the top of page two."
    cross_pdf = fixtures / "synthetic_crosspage.pdf"
    cross_pdf.write_bytes(build_pdf([[head], [tail]]))
    outcome = locate(cross_pdf, f"{head} {tail}", (1, 2), args.out_dir, "crosspage")
    record(
        probes,
        "cross_page",
        "located with one fragment on page 1 and one on page 2",
        outcome,
        ok=outcome["status"] == "located" and pages_of(outcome) == [1, 2],
    )

    # --- 5. rotation sweep ------------------------------------------------- #
    line_a = "Rotated page probe line one."
    line_b = "Rotated page probe line two."
    for rotation in (0, 90, 180, 270):
        rotated_pdf = fixtures / f"synthetic_rotated_{rotation}.pdf"
        rotated_pdf.write_bytes(build_pdf([[line_a, line_b]], rotate=rotation))

        # each line on its own must locate and land on glyphs
        per_line: list[dict] = []
        for position, line in enumerate((line_a, line_b), start=1):
            outcome = locate(
                rotated_pdf, line, (1, 1), args.out_dir,
                f"rot{rotation}_line{position}",
            )
            fragment = outcome["fragments"][0] if outcome["fragments"] else {}
            per_line.append(
                {
                    "line": position,
                    "status": outcome["status"],
                    "geometry_ok": fragment.get("geometry_ok", False),
                    "ink_ratio_min": min(fragment.get("ink_ratios", [0.0])),
                    "rotation_reported": fragment.get("page_meta", {}).get("rotation"),
                }
            )
        lines_ok = all(
            detail["status"] == "located" and detail["geometry_ok"]
            for detail in per_line
        )

        forward = locate(
            rotated_pdf, f"{line_a} {line_b}", (1, 1), args.out_dir,
            f"rot{rotation}_forward",
        )
        backwards = locate(
            rotated_pdf, f"{line_b} {line_a}", (1, 1), args.out_dir,
            f"rot{rotation}_displayorder",
        )
        # The multi-line passage must exist in the extracted text in exactly one
        # of the two possible line orders; which one PDFium returns is recorded
        # as an observation (it is a text-ordering property, not a geometry one).
        if forward["status"] == "located":
            observed_order = "content_order"
        elif backwards["status"] == "located":
            observed_order = "display_order"
        else:
            observed_order = "neither"
        order_ok = observed_order != "neither"
        probes.append(
            {
                "probe": f"rotated_page_{rotation}",
                "expectation": (
                    "each line locates with highlight on glyphs; the multi-line "
                    "passage is present in one of the two line orders"
                ),
                "status": forward["status"],
                "search_scope": forward["search_scope"],
                "hint_confirmed": forward["hint_confirmed"],
                "fragments": len(forward["fragments"]),
                "pages": pages_of(forward),
                "artifacts": len(forward["artifacts"]),
                "fragment_details": forward["fragment_details"],
                "per_line": per_line,
                "observed_line_order": observed_order,
                "content_order_join_status": forward["status"],
                "display_order_join_status": backwards["status"],
                "naive_mediabox_ink_ratio": (
                    naive_yflip_ink(rotated_pdf, f"{line_a} {line_b}", (1, 1))
                    if rotation == 90
                    else None
                ),
                "ok": lines_ok and order_ok,
            }
        )

    # --- 6. cropped page --------------------------------------------------- #
    cropped_pdf = fixtures / "synthetic_cropped.pdf"
    cropped_pdf.write_bytes(
        build_pdf(
            [["Cropped page probe line one.", "Cropped page probe line two."]],
            mediabox=(0.0, 0.0, 612.0, 792.0),
            cropbox=(0.0, 300.0, 612.0, 792.0),
            origin=(72.0, 700.0),
        )
    )
    outcome = locate(
        cropped_pdf, "Cropped page probe line one. Cropped page probe line two.",
        (1, 1), args.out_dir, "cropped",
    )
    record(
        probes,
        "cropped_page",
        "located, highlight inside the crop box (crop-aware pixel conversion)",
        outcome,
        ok=outcome["status"] == "located"
        and outcome["fragments"][0].get("geometry_ok", False),
    )

    # --- 7. no text layer -> needs_ocr ------------------------------------ #
    vector_pdf = fixtures / "synthetic_no_text_layer.pdf"
    vector_pdf.write_bytes(build_pdf([[]], draw_only=True))
    outcome = locate(vector_pdf, "Any text at all.", (1, 1), args.out_dir, "no_text_layer")
    record(
        probes,
        "no_text_layer",
        "needs_ocr, no highlight",
        outcome,
        ok=outcome["status"] == "needs_ocr" and not outcome["artifacts"],
    )

    # --- 8. wrong stored page hint -> whole-PDF fallback ------------------ #
    candidates = ev.load_candidates(args.results)
    gold = next(item for item in candidates if item["candidate_id"] == "rank-05")
    outcome = locate(args.pdf, gold["text"], (500, 500), args.out_dir, "hint_wrong")
    record(
        probes,
        "wrong_hint_fallback",
        "located on PDF page 109 via whole-PDF fallback, hint_confirmed=False",
        outcome,
        ok=outcome["status"] == "located"
        and pages_of(outcome) == [109]
        and outcome["hint_confirmed"] is False,
    )

    # --- 9. whitespace variant of the real gold candidate ----------------- #
    rewritten = gold["text"].replace("\n", " ").replace(" ", "   ")
    outcome = locate(args.pdf, rewritten, (109, 109), args.out_dir, "gold_whitespace")
    record(
        probes,
        "real_gold_whitespace_rewrite",
        "located on PDF page 109, same character span as the stored candidate",
        outcome,
        ok=outcome["status"] == "located"
        and pages_of(outcome) == [109]
        and outcome["located_norm_chars"] == outcome["norm_query_chars"],
    )

    passed = sum(1 for probe in probes if probe["ok"])
    summary = {
        "probe_count": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "api_calls": 0,
        "api_cost_usd": 0.0,
        "fixtures_are_synthetic": True,
        "probes": probes,
    }
    report_path = args.out_dir / "t003_probe_summary.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    for probe in probes:
        naive = probe.get("naive_mediabox_ink_ratio")
        print(
            f"{'PASS' if probe['ok'] else 'FAIL'}  {probe['probe']:<28} "
            f"status={probe['status']:<9} pages={probe['pages']} "
            f"fragments={probe['fragments']} artifacts={probe['artifacts']}"
            + (f" naive_ink={naive}" if naive else "")
        )
    print(f"\n{passed}/{len(probes)} probes passed; report: {report_path}")
    return 0 if passed == len(probes) else 1


if __name__ == "__main__":
    sys.exit(main())

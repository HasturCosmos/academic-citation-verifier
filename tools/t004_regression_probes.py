#!/usr/bin/env python
"""T004 regression probes for the backend slice's product-facing layers.

These probes cover what T003's probes cannot: the evidence *object* contract and
the citation shells. They run entirely on synthetic, non-private fixtures (and
one in-memory metadata record), make no model/API call, and print aggregates
only.

Probed behaviours:

* ``located / ambiguous / unmatched / needs_ocr`` all reach the product object;
* only ``located`` candidates carry images, and cross-page candidates carry one
  image per PDF page;
* a wrong stored hint falls back to the whole document and is reported;
* the citation builder emits a page segment only when a printed page is
  confirmed, and never invents a missing field;
* PDF sequence pages and printed book pages stay separate fields;
* the gold-passage tolerance used by the acceptance check neither fires on
  unrelated text nor accepts more extra characters than allowed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import t003_evidence_localize as ev  # noqa: E402
import t003_regression_probes as t003  # noqa: E402
import t004_backend_slice as t004  # noqa: E402

DEFAULT_OUT = ev.REPO_ROOT / "data/private/C04/t004/probes"

CONFIRMED_METADATA = {
    "document_id": "probe-document",
    "author": "测试作者",
    "author_country": "德",
    "title": "测试文献",
    "volume": "第一卷",
    "document_type": "M",
    "translator": "测试译者",
    "publisher_place": "上海",
    "publisher": "测试出版社",
    "year": "2019",
    "metadata_origin": "synthetic fixture for T004 probes",
}


def record(probes: list[dict], name: str, expectation: str, ok: bool, **extra) -> None:
    probes.append(
        {"probe": name, "expectation": expectation, "ok": bool(ok), **extra}
    )


def build_objects(pdf: Path, candidates: list[dict], out_dir: Path, metadata: dict) -> dict:
    return t004.build_result(
        candidates=candidates,
        pdf_path=pdf,
        document_id=str(metadata.get("document_id")),
        metadata=metadata,
        out_dir=out_dir,
        dpi=144.0,
        radius=1,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    out_dir = args.out_dir
    fixtures = out_dir / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    probes: list[dict] = []

    # ------------------------------------------------------------------ #
    # 1. synthetic two-page document and the candidate outcomes
    # ------------------------------------------------------------------ #
    alpha = "Probe alpha sentence one."
    ambiguous = "Ambiguity sentence."
    missing = "This text does not occur anywhere in the document."
    cross = "Probe cross page tail one."
    pdf = fixtures / "t004_synthetic.pdf"
    # ``alpha`` is the last line of page 1 and ``cross`` the first line of page 2,
    # so ``{alpha} {cross}`` is one contiguous passage split by the page break.
    pdf.write_bytes(
        t003.build_pdf([[ambiguous, ambiguous, alpha], [cross]])
    )

    candidates = [
        {"candidate_id": "cand-01", "rank": 1, "score": 9,
         "page_label": "probe.pdf pages 1-1", "text": alpha},
        {"candidate_id": "cand-02", "rank": 2, "score": 7,
         "page_label": "probe.pdf pages 1-1", "text": ambiguous},
        {"candidate_id": "cand-03", "rank": 3, "score": 3,
         "page_label": "probe.pdf pages 1-1", "text": missing},
        {"candidate_id": "cand-04", "rank": 4, "score": 8,
         "page_label": "probe.pdf pages 1-2", "text": f"{alpha} {cross}"},
        {"candidate_id": "cand-05", "rank": 5, "score": 6,
         "page_label": "probe.pdf pages 99-99", "text": alpha},
    ]
    result = build_objects(pdf, candidates, out_dir / "located_run", CONFIRMED_METADATA)
    objects = {item["candidate_id"]: item for item in result["candidates"]}

    statuses = {key: item["status"] for key, item in objects.items()}
    record(
        probes,
        "statuses_reach_product_object",
        "located/ambiguous/unmatched all represented with explicit statuses",
        statuses
        == {
            "cand-01": "located",
            "cand-02": "ambiguous",
            "cand-03": "unmatched",
            "cand-04": "located",
            "cand-05": "located",
        },
        statuses=statuses,
    )
    record(
        probes,
        "images_only_for_located",
        "only located candidates carry highlight images",
        all(
            bool(item["highlighted_image_refs"]) == (item["status"] == "located")
            for item in objects.values()
        ),
        images={key: len(item["highlighted_image_refs"]) for key, item in objects.items()},
    )
    record(
        probes,
        "cross_page_two_images",
        "cross-page candidate yields one image per PDF page",
        objects["cand-04"]["pdf_page_numbers"] == [1, 2]
        and len(objects["cand-04"]["highlighted_image_refs"]) == 2,
        pages=objects["cand-04"]["pdf_page_numbers"],
    )
    record(
        probes,
        "wrong_hint_fallback_reported",
        "wrong stored hint still locates via whole-document fallback and says so",
        objects["cand-05"]["localization"]["hint_confirmed"] is False
        and objects["cand-05"]["pdf_page_numbers"] == [1]
        and any("fallback" in warning for warning in objects["cand-05"]["warnings"]),
        hint_confirmed=objects["cand-05"]["localization"]["hint_confirmed"],
    )
    record(
        probes,
        "ambiguous_and_unmatched_warn",
        "ambiguous/unmatched candidates carry warnings and no geometry",
        any("no guessed highlight" in warning for warning in objects["cand-02"]["warnings"])
        and any("no full match" in warning for warning in objects["cand-03"]["warnings"])
        and not objects["cand-02"]["fragments"]
        and not objects["cand-03"]["fragments"],
    )

    required_keys = {
        "candidate_id",
        "status",
        "source_document_id",
        "retrieval_rank",
        "original_text",
        "pdf_page_numbers",
        "highlighted_image_refs",
        "original_page_image_refs",
        "bibliographic_metadata",
        "basic_footnote_citation",
        "basic_reference_citation",
        "warnings",
        "unresolved_fields",
    }
    missing_keys = sorted(
        {
            key
            for item in result["candidates"]
            for key in required_keys - set(item)
        }
    )
    record(
        probes,
        "evidence_object_schema",
        "every candidate object carries the required product fields",
        not missing_keys,
        missing_keys=missing_keys,
    )
    record(
        probes,
        "multiple_candidates_preserved",
        "all five candidates stay in the result in retrieval order",
        [item["candidate_id"] for item in result["candidates"]]
        == ["cand-01", "cand-02", "cand-03", "cand-04", "cand-05"],
    )
    record(
        probes,
        "pdf_pages_not_printed_pages",
        "PDF page numbers and printed book pages stay separate; printed page unresolved",
        all(item["printed_page_numbers"] == [] for item in result["candidates"])
        and all("printed_page" in item["unresolved_fields"] for item in result["candidates"])
        and objects["cand-01"]["pdf_page_numbers"] == [1],
    )

    # ------------------------------------------------------------------ #
    # 2. citation assembly
    # ------------------------------------------------------------------ #
    no_page = t004.build_citations(CONFIRMED_METADATA, printed_page=None)
    page = t004.build_citations(CONFIRMED_METADATA, printed_page="118-119")
    expected_footnote = "[德]测试作者：《测试文献（第一卷）》，测试译者译，上海：测试出版社，2019年。"
    expected_reference = "[德]测试作者.测试文献（第一卷）[M].测试译者译.上海:测试出版社,2019."
    record(
        probes,
        "citation_page_only_when_confirmed",
        "page segment appears only when a printed page is confirmed",
        no_page["basic_footnote_citation"] == expected_footnote
        and no_page["basic_reference_citation"] == expected_reference
        and page["basic_footnote_citation"]
        == expected_footnote[:-1] + "，第118-119页。"
        and page["basic_reference_citation"]
        == expected_reference[:-1] + ":118-119.",
        footnote_no_page=no_page["basic_footnote_citation"],
        footnote_with_page=page["basic_footnote_citation"],
    )
    record(
        probes,
        "unresolved_fields_listed",
        "unknown printed page is listed as unresolved instead of guessed",
        no_page["unresolved_fields"] == ["printed_page"],
        unresolved=no_page["unresolved_fields"],
    )

    partial = dict(CONFIRMED_METADATA)
    partial.pop("translator")
    partial_citation = t004.build_citations(partial)
    record(
        probes,
        "missing_translator_not_invented",
        "a missing translator is omitted from the string and listed as unresolved",
        "译" not in partial_citation["basic_reference_citation"]
        and "translator" in partial_citation["unresolved_fields"]
        and not any(
            token in partial_citation["basic_reference_citation"]
            for token in ("None", "Unknown", "未知")
        ),
        reference=partial_citation["basic_reference_citation"],
    )

    anonymised = {key: value for key, value in CONFIRMED_METADATA.items()
                  if key not in {"author", "title"}}
    anonymised_citation = t004.build_citations(anonymised)
    record(
        probes,
        "no_citation_without_author_title",
        "with no confirmed author/title no citation shell is produced at all",
        anonymised_citation["basic_footnote_citation"] is None
        and anonymised_citation["basic_reference_citation"] is None
        and set(anonymised_citation["unresolved_fields"]) >= {"author", "title"},
    )

    # ------------------------------------------------------------------ #
    # 3. needs_ocr reaches the product object
    # ------------------------------------------------------------------ #
    vector_pdf = fixtures / "t004_no_text_layer.pdf"
    vector_pdf.write_bytes(t003.build_pdf([[]], draw_only=True))
    ocr_result = build_objects(
        vector_pdf,
        [
            {
                "candidate_id": "cand-01",
                "rank": 1,
                "score": 5,
                "page_label": "probe.pdf pages 1-1",
                "text": missing,
            }
        ],
        out_dir / "needs_ocr_run",
        CONFIRMED_METADATA,
    )
    ocr_object = ocr_result["candidates"][0]
    record(
        probes,
        "needs_ocr_reaches_product_object",
        "a page without a text layer reports needs_ocr with no geometry",
        ocr_object["status"] == "needs_ocr"
        and not ocr_object["highlighted_image_refs"]
        and any("OCR" in warning for warning in ocr_object["warnings"]),
        status=ocr_object["status"],
    )

    # ------------------------------------------------------------------ #
    # 4. containment tolerance used by the acceptance check
    # ------------------------------------------------------------------ #
    # Deliberately a synthetic sentence: the real gold passage is private source
    # text and is only ever read from the private case at run time by the
    # acceptance run, never embedded in a tracked file.
    needle = "合成测试句子用于验证容错匹配逻辑不依赖任何私有文本内容"
    interrupted = needle[:14] + "7" + needle[14:]
    record(
        probes,
        "tolerance_accepts_inserted_character",
        "one inserted character inside a passage is tolerated and reported",
        t004.fuzzy_contains(needle, interrupted) == (True, 1, "Nd"),
        result=t004.fuzzy_contains(needle, interrupted),
    )
    record(
        probes,
        "tolerance_has_a_bound",
        "tolerance is bounded and does not match unrelated text",
        t004.fuzzy_contains(needle, interrupted, max_extra_chars=0)[0] is False
        and t004.fuzzy_contains(needle, "完全无关的一段文字")[0] is False,
    )
    record(
        probes,
        "tolerance_no_false_positive_on_probe_corpus",
        "no probe document text is misread as the synthetic passage",
        not any(
            t004.fuzzy_contains(needle, t004.core_chars(item["original_text"]))[0]
            for item in result["candidates"]
        ),
    )

    passed = sum(1 for probe in probes if probe["ok"])
    summary = {
        "probe_count": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "api_calls": 0,
        "api_cost_usd": 0.0,
        "probes": probes,
    }
    report_path = out_dir / "t004_probe_summary.json"
    report_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for probe in probes:
        print(
            f"{'PASS' if probe['ok'] else 'FAIL'}  {probe['probe']:<42} "
            f"{probe['expectation']}"
        )
    print(f"\n{passed}/{len(probes)} probes passed; report: {report_path}")
    return 0 if passed == len(probes) else 1


if __name__ == "__main__":
    raise SystemExit(main())

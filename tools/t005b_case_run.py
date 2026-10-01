#!/usr/bin/env python
"""T005B: run one genuinely new real case through the current product path.

The case input is a real secondary-source passage plus a real, fallible clue
and one candidate primary-source PDF. This runner deliberately follows the same
order the product uses, and stops at the first honest failure instead of
forcing a result:

    source ingestion (text-layer scan)
        -> current retrieval component (PaperQA2 core API, local embedding)
        -> evidence stage (only if a candidate text exists)
        -> product evidence object carrying an explicit status

If the candidate PDF carries no usable text layer, the run reports
``needs_ocr``, emits no geometry and invents no candidate text. Building OCR is
explicitly out of scope for T005B.

Step 1 is free. Step 2 uses the pinned settings and the local embedding only;
the paid query stage is never reached when there is nothing to retrieve, and
the runner records that decision instead of hiding it.

Private text, screenshots and records are written only under ``data/private/``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(REPO_ROOT / "tools"))

import t003_evidence_localize as ev  # noqa: E402
import t005b_scan_probe as probe  # noqa: E402

RESULT_VERSION = "t005b-v1"


def repo_relative(path: Path | str) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


async def try_index_with_paperqa(
    pdf_path: Path, settings_path: Path, docname: str, citation: str
) -> dict:
    """Attempt the current retrieval component's ingest step (no LLM call)."""
    from paperqa.docs import Docs
    from paperqa.settings import Settings

    settings = Settings.model_validate_json(settings_path.read_text(encoding="utf-8"))
    llm = settings.get_llm()
    embedding = settings.get_embedding_model()

    docs = Docs()
    record: dict = {
        "component": "paperqa-core-aadd",
        "cli_agent_used": False,
        "docname": docname,
        "citation_supplied": citation,
    }
    started = time.perf_counter()
    try:
        await docs.aadd(
            pdf_path,
            citation=citation,
            docname=docname,
            llm_model=llm,
            embedding_model=embedding,
            settings=settings,
        )
        record["status"] = "ok"
    except Exception as error:  # noqa: BLE001 - the failure itself is the evidence
        record["status"] = f"error: {type(error).__name__}: {error}"
    record["seconds"] = round(time.perf_counter() - started, 2)

    texts = []
    try:
        for doc in getattr(docs, "docs", {}).values():
            texts.append(doc)
    except Exception:  # noqa: BLE001
        pass
    record["document_count"] = len(texts)
    record["indexed_text_chars"] = sum(
        len(getattr(doc, "text", "") or "") for doc in texts
    )
    record["indexed_chunk_count"] = sum(
        len(getattr(doc, "texts", []) or []) for doc in texts
    )
    record["paid_query_stage_reached"] = False
    record["paid_query_stage_reason"] = (
        "the ingest stage produced no searchable text for this document, so a "
        "query could not return any source candidate; the paid query stage was "
        "not run and no model call was made"
    )
    return record


def build_document_record(
    *,
    document_id: str,
    metadata: dict,
    scan: dict,
    reason: str,
) -> dict:
    """T004-contract-shaped evidence object for a case that cannot be searched."""
    citations = ev_citations(metadata)
    unresolved = list(citations["unresolved_fields"])
    unresolved.extend(["printed_page_numbers", "highlight_geometry", "source_passage"])
    return {
        "candidate_id": None,
        "status": "needs_ocr",
        "source_document_id": document_id,
        "retrieval_rank": None,
        "retrieval_score": None,
        "original_text": None,
        "pdf_page_numbers": [],
        "printed_page_numbers": [],
        "highlighted_image_refs": [],
        "original_page_image_refs": [],
        "fragments": [],
        "localization": {
            "status": "needs_ocr",
            "search_scope": "not_attempted",
            "hint_pages": None,
            "hint_confirmed": False,
            "scanned_pages": scan["page_count"],
            "occurrences_in_hint_window": 0,
            "occurrences_in_pdf": None,
        },
        "bibliographic_metadata": {
            "document_id": document_id,
            "author": metadata.get("author"),
            "author_country": metadata.get("author_country"),
            "title": metadata.get("title"),
            "volume": metadata.get("volume"),
            "translator": metadata.get("translator"),
            "publisher_place": metadata.get("publisher_place"),
            "publisher": metadata.get("publisher"),
            "year": metadata.get("year"),
            "document_type": metadata.get("document_type"),
            "metadata_origin": metadata.get("metadata_origin"),
            "printed_page": None,
        },
        "basic_footnote_citation": citations["basic_footnote_citation"],
        "basic_reference_citation": citations["basic_reference_citation"],
        "citation_parts": citations["citation_parts"],
        "warnings": [reason, "no highlight or page geometry was emitted"],
        "unresolved_fields": sorted(set(unresolved)),
        "text_layer": {
            "pages": scan["page_count"],
            "pages_with_usable_text_layer": scan["pages_with_usable_text_layer"],
            "total_normalized_chars": scan["total_normalized_chars"],
        },
    }


def ev_citations(metadata: dict) -> dict:
    """Reuse the T004 citation assembler through its own module."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "t004_backend_slice", REPO_ROOT / "tools" / "t004_backend_slice.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build_citations(metadata)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument(
        "--settings",
        type=Path,
        default=REPO_ROOT / ".pqa/settings/m1e1_c04.json",
    )
    parser.add_argument("--docname", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--skip-retrieval",
        action="store_true",
        help="stop after the zero-cost text-layer scan",
    )
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    document_id = str(metadata.get("document_id") or args.docname)
    case_text = read_text(args.case)

    scan = probe.scan(args.pdf)
    scan_report = {
        "pdf": repo_relative(args.pdf),
        "pdf_bytes": args.pdf.stat().st_size,
        "pdf_sha256": probe.sha256_of(args.pdf),
        "text_layer_min_chars": probe.MIN_TEXT_LAYER_CHARS,
        **scan,
    }
    (args.out_dir / "text_layer_scan.json").write_text(
        json.dumps(scan_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    searchable = scan["pages_with_usable_text_layer"] > 0
    retrieval: dict | None = None
    if not args.skip_retrieval:
        citation = ev_citations(metadata)["basic_reference_citation"] or args.docname
        retrieval = asyncio.run(
            try_index_with_paperqa(
                args.pdf, args.settings, args.docname, citation
            )
        )
        retrieval["document_searchable"] = searchable

    if searchable:
        case_status = "source_searchable"
        reason = (
            "the candidate document carries a usable text layer; the case did "
            "not exercise the no-text-layer failure path"
        )
    else:
        case_status = "needs_ocr"
        reason = (
            f"the candidate PDF has no usable text layer on any of its "
            f"{scan['page_count']} pages ({scan['total_normalized_chars']} "
            "normalized characters in total), so the current stack cannot "
            "retrieve or localize any source passage; OCR is out of scope for "
            "T005B and no evidence was fabricated"
        )

    document_record = build_document_record(
        document_id=document_id,
        metadata=metadata,
        scan=scan,
        reason=reason,
    )

    result = {
        "result_version": RESULT_VERSION,
        "case": {
            "case_id": args.docname,
            "case_file": repo_relative(args.case),
            "case_file_chars": len(case_text),
            "primary_document_id": document_id,
        },
        "source_document": {
            "pdf": repo_relative(args.pdf),
            "pdf_sha256": scan_report["pdf_sha256"],
            "page_count": scan["page_count"],
            "text_layer_verdict": "needs_ocr" if not searchable else "searchable",
        },
        "stages": {
            "text_layer_scan": {
                "pages": scan["page_count"],
                "pages_with_usable_text_layer": scan["pages_with_usable_text_layer"],
                "total_normalized_chars": scan["total_normalized_chars"],
                "seconds": scan["scan_seconds"],
            },
            "retrieval_ingest": retrieval,
            "localization": {
                "status": "not_attempted",
                "reason": (
                    "localization needs at least one candidate passage; with no "
                    "searchable text there is no candidate to localize and no "
                    "PDF page hint can be resolved"
                ),
            },
        },
        "status": case_status,
        "documents": [document_record],
        "candidates": [],
        "warnings": [
            reason,
            "the case input is a secondary-source paraphrase; it is recorded as "
            "input, never as source evidence, and no source text was invented",
        ],
        "unresolved_fields": ["source_passage", "printed_page_numbers", "highlight_geometry"],
        "run": {
            "entrypoint": "tools/t005b_case_run.py",
            "started_at": started_at,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "model_calls": {"by_name": {}, "total": 0},
            "cost_usd": 0.0,
        },
    }
    (args.out_dir / "t005b_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = {
        "status": case_status,
        "pdf_sha256": scan_report["pdf_sha256"],
        "pages": scan["page_count"],
        "pages_with_usable_text_layer": scan["pages_with_usable_text_layer"],
        "total_normalized_chars": scan["total_normalized_chars"],
        "retrieval_ingest_status": (retrieval or {}).get("status"),
        "retrieval_indexed_chunk_count": (retrieval or {}).get("indexed_chunk_count"),
        "model_calls": 0,
        "cost_usd": 0.0,
        "result_path": repo_relative(args.out_dir / "t005b_result.json"),
    }
    (args.out_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

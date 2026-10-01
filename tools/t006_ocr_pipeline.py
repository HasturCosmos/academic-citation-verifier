#!/usr/bin/env python
"""T006 Phase 2 (experimental): image-only scan -> OCR -> retrieval -> evidence.

This is the experimental integration the overnight brief allows *only* if the
benchmark evidence supports it. It is deliberately thin and it reuses every
proven component instead of forking a second pipeline:

1. **OCR**        — RapidOCR (``t006_ocr_evidence``), cached per page, resumable.
2. **Chunking**   — upstream ``paperqa.readers.chunk_pdf`` with the pinned
   ``chunk_chars``/``overlap``, so chunks keep the same ``"<doc> pages N-M"``
   page-range label that the T003 adapter already understands.
3. **Retrieval**  — upstream ``paperqa.docs.Docs.aadd_texts`` +
   ``Docs.retrieve_texts`` with the pinned local embedding. **No LLM call is
   made**: this path is embedding-only, so it costs $0.00 and never invents a
   model-written summary.
4. **Evidence**   — the unchanged T004 evidence-object builder fed by an
   OCR-backed ``PdfEvidenceSource`` subclass, so statuses, page provenance,
   highlight geometry and citation honesty rules are identical to T004.

Honesty rules kept from T003/T004/T005B:

* OCR text is *not* source truth: every evidence object carries an explicit
  warning that the text came from OCR and needs page-image verification.
* the secondary-source passage is the query, never the evidence;
* no page number, quotation or highlight is invented when localization fails;
* private text and page images stay under ``data/private/``.

Experimental status: this module is an optional, reversible experiment. It does
not replace the default text-layer path and does not constitute architecture
adoption.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import t003_evidence_localize as ev  # noqa: E402
import t004_backend_slice as t004  # noqa: E402
import t006_ocr_evidence as oe  # noqa: E402

DEFAULT_SETTINGS = REPO_ROOT / ".pqa/settings/m1e1_c04.json"
DEFAULT_METADATA = REPO_ROOT / "data/private/T005B-01/inputs/primary_document.json"
DEFAULT_QUERY = REPO_ROOT / "data/private/T005B-01/inputs/query.txt"
DEFAULT_OCR_CACHE = oe.DEFAULT_CACHE_DIR
DEFAULT_OUT_DIR = REPO_ROOT / "data/private/T006-01/ocr_run"

OCR_WARNING = (
    "experimental OCR path: this passage was recognised by RapidOCR from the "
    "scanned page image, not read from a publisher text layer; verify it against "
    "the page image before citing it"
)


# --------------------------------------------------------------------------- #
# index building (reuse of the upstream chunker + retrieval component)
# --------------------------------------------------------------------------- #


def build_ocr_chunks(
    ocr_pages: dict[int, dict],
    *,
    docname: str,
    citation: str,
    chunk_chars: int,
    overlap: int,
) -> tuple[object, list]:
    """Chunk the OCR page text exactly like PaperQA2 chunks a parsed PDF."""
    from paperqa.docs import Doc
    from paperqa.readers import ParsedMetadata, ParsedText, chunk_pdf

    content = {
        str(page_number): record["joined_text"]
        for page_number, record in sorted(ocr_pages.items())
        if record.get("joined_text")
    }
    if not content:
        raise SystemExit("no OCR text available; run the OCR cache first")

    parsed_text = ParsedText(
        content=content,
        metadata=ParsedMetadata(
            parsing_libraries=[f"rapidocr (ocr cache: {len(content)} pages)"],
            total_parsed_text_length=sum(len(text) for text in content.values()),
            name="t006-ocr",
        ),
    )
    doc = Doc(dockey=str(uuid.uuid4()), docname=docname, citation=citation)
    chunks = chunk_pdf(parsed_text, doc, chunk_chars=chunk_chars, overlap=overlap)
    return doc, chunks


async def build_index(chunks: list, doc, settings):
    from paperqa.docs import Docs

    embedding = settings.get_embedding_model()
    docs = Docs()
    ok = await docs.aadd_texts(
        chunks, doc=doc, settings=settings, embedding_model=embedding
    )
    return docs, embedding, bool(ok)


async def retrieve(docs, embedding, query: str, k: int, settings) -> list:
    return await docs.retrieve_texts(
        query, k=k, settings=settings, embedding_model=embedding
    )


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #


def load_settings(path: Path):
    from paperqa.settings import Settings

    return Settings.model_validate_json(path.read_text(encoding="utf-8"))


def _reader_config_value(config, key: str, default: int) -> int:
    """``parsing.reader_config`` is a plain dict in the pinned PaperQA2 build."""
    if config is None:
        return default
    if isinstance(config, dict):
        return int(config.get(key, default))
    return int(getattr(config, key, default))


def run(
    *,
    pdf_path: Path,
    ocr_cache: Path,
    metadata: dict,
    query: str,
    out_dir: Path,
    dpi: float,
    k: int,
    settings_path: Path,
    radius: int = 1,
    docname: str,
    citation: str,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    settings = load_settings(settings_path)
    ocr_pages = oe.load_cached_pages(ocr_cache)
    if not ocr_pages:
        raise SystemExit(f"no OCR cache at {ocr_cache}")

    reader = settings.parsing.reader_config
    chunk_chars = _reader_config_value(reader, "chunk_chars", 400)
    chunk_overlap = _reader_config_value(reader, "overlap", 100)
    started = time.perf_counter()
    doc, chunks = build_ocr_chunks(
        ocr_pages,
        docname=docname,
        citation=citation,
        chunk_chars=chunk_chars,
        overlap=chunk_overlap,
    )
    docs, embedding, indexed = asyncio.run(build_index(chunks, doc, settings))
    index_seconds = round(time.perf_counter() - started, 1)

    retrieval_started = time.perf_counter()
    matches = asyncio.run(retrieve(docs, embedding, query, k, settings))
    retrieval_seconds = round(time.perf_counter() - retrieval_started, 1)

    candidates = [
        {
            "candidate_id": f"rank-{rank:02d}",
            "rank": rank,
            "score": None,
            "page_label": match.name,
            "text": match.text,
        }
        for rank, match in enumerate(matches, start=1)
    ]

    source = oe.OcrEvidenceSource(pdf_path, ocr_pages, dpi=dpi)
    objects: list[dict] = []
    try:
        for candidate in candidates:
            record = t004.build_evidence_object(
                candidate,
                source,
                document_id=metadata.get("document_id") or docname,
                metadata=metadata,
                images_dir=images_dir,
                dpi=dpi,
                radius=radius,
            )
            record["evidence_origin"] = "ocr"
            record["warnings"] = [OCR_WARNING, *record.get("warnings", [])]
            record["unresolved_fields"] = sorted(
                set(record.get("unresolved_fields", []))
                | {"ocr_text_verification"}
            )
            objects.append(record)
            print(
                f"[{record['candidate_id']}] status={record['status']} "
                f"pages={record['pdf_page_numbers']} "
                f"label={record['retrieval_page_label']}",
                flush=True,
            )
    finally:
        source.close()

    summary = {
        "result_version": "t006-ocr-pipeline-v1",
        "experimental": True,
        "entrypoint": "tools/t006_ocr_pipeline.py",
        "source_pdf": oe.repo_relative(pdf_path),
        "source_pdf_sha256": t004.ev.sha256_of(pdf_path),
        "ocr_cache": oe.repo_relative(ocr_cache),
        "ocr_engine": next(iter(ocr_pages.values())).get("engine", "rapidocr"),
        "ocr_pages": len(ocr_pages),
        "ocr_pages_without_text": sum(
            1
            for record in ocr_pages.values()
            if record["char_count"] < ev.MIN_TEXT_LAYER_CHARS
        ),
        "ocr_total_chars": sum(record["char_count"] for record in ocr_pages.values()),
        "chunker": "paperqa.readers.chunk_pdf",
        "chunk_chars": chunk_chars,
        "chunk_overlap": chunk_overlap,
        "chunk_count": len(chunks),
        "indexed": indexed,
        "retrieval": "paperqa.docs.Docs.retrieve_texts (local embedding, no LLM)",
        "embedding": str(settings.embedding),
        "k": k,
        "index_seconds": index_seconds,
        "retrieval_seconds": retrieval_seconds,
        "model_calls": 0,
        "cost_usd": 0.0,
        "statuses": {
            status: sum(1 for obj in objects if obj["status"] == status)
            for status in t004.STATUS_VALUES
        },
        "located_pages": sorted(
            {
                page
                for obj in objects
                for page in obj["pdf_page_numbers"]
            }
        ),
    }
    (out_dir / "ocr_candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "evidence_objects.json").write_text(
        json.dumps(objects, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "evidence_report.html").write_text(
        render_report(summary, objects, query, base_dir=out_dir), encoding="utf-8"
    )
    return summary


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #


def render_report(
    summary: dict, objects: list[dict], query: str, base_dir: Path | None = None
) -> str:
    parts: list[str] = []
    parts.append("<!doctype html><html lang='zh'><meta charset='utf-8'>")
    parts.append(
        "<title>T006 experimental OCR evidence report</title>"
        "<style>body{font-family:system-ui,'Microsoft YaHei',sans-serif;"
        "max-width:1100px;margin:24px auto;line-height:1.6}"
        ".status{display:inline-block;padding:2px 8px;border-radius:10px;"
        "font-size:12px;color:#fff}"
        ".located{background:#2e7d32}.ambiguous{background:#ef6c00}"
        ".unmatched{background:#c62828}.needs_ocr{background:#455a64}"
        ".warn{background:#fff8e1;border-left:4px solid #ffb300;padding:8px}"
        "img{max-width:100%;border:1px solid #ccc;margin-top:8px}"
        "pre{white-space:pre-wrap;background:#f6f6f6;padding:8px}</style>"
    )
    parts.append("<h1>T006 experimental OCR evidence report</h1>")
    parts.append(
        "<p class='warn'><b>Experimental demo.</b> This is not the final UI, not "
        "a durable OCR adoption, and OCR text must be verified against the page "
        "image before it is used as evidence.</p>"
    )
    parts.append("<h2>Run</h2><ul>")
    for key in (
        "source_pdf",
        "ocr_engine",
        "ocr_pages",
        "ocr_total_chars",
        "chunk_count",
        "retrieval",
        "embedding",
        "k",
        "index_seconds",
        "retrieval_seconds",
        "model_calls",
        "cost_usd",
    ):
        parts.append(f"<li>{html.escape(key)}: {html.escape(str(summary[key]))}</li>")
    parts.append("</ul>")
    parts.append(
        "<h2>Secondary-source input (query, never evidence)</h2><pre>"
        + html.escape(query)
        + "</pre>"
    )
    parts.append("<h2>Statuses</h2><ul>")
    for status, count in summary["statuses"].items():
        parts.append(f"<li>{status}: {count}</li>")
    parts.append("</ul>")

    for obj in objects:
        parts.append("<hr>")
        parts.append(
            f"<h3>{html.escape(obj['candidate_id'])} "
            f"<span class='status {obj['status']}'>{obj['status']}</span></h3>"
        )
        parts.append(
            "<ul>"
            f"<li>retrieval page label: {html.escape(str(obj.get('retrieval_page_label')))}</li>"
            f"<li>resolved PDF pages: {obj['pdf_page_numbers']}</li>"
            f"<li>printed page: unresolved (never substituted)</li>"
            f"<li>footnote: {html.escape(str(obj.get('basic_footnote_citation')))}</li>"
            f"<li>reference: {html.escape(str(obj.get('basic_reference_citation')))}</li>"
            "</ul>"
        )
        if obj.get("original_text"):
            parts.append(
                "<p><b>Retrieved source text (OCR)</b></p><pre>"
                + html.escape(obj["original_text"])
                + "</pre>"
            )
        for warning in obj.get("warnings", []):
            parts.append(f"<p class='warn'>{html.escape(warning)}</p>")
        for ref in obj.get("highlighted_image_refs", []):
            parts.append(
                f"<div><img src='{html.escape(_relative_ref(ref, base_dir))}' "
                f"alt='highlighted page'></div>"
            )
    parts.append("</html>")
    return "\n".join(parts)


def _relative_ref(ref: str, base_dir: Path | None = None) -> str:
    """Path for an ``<img src>`` relative to the HTML file, in URL form.

    The report lives next to its ``images/`` directory, so references must be
    relative to the report, not to the process working directory — otherwise
    opening the HTML directly from disk shows broken images.
    """
    path = Path(ref)
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    try:
        relative = os.path.relpath(path.resolve(), base.resolve())
    except ValueError:
        return path.as_posix()
    return Path(relative).as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--ocr-cache", type=Path, default=DEFAULT_OCR_CACHE)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--query-file", type=Path, default=DEFAULT_QUERY)
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dpi", type=float, default=ev.DEFAULT_DPI)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--docname", default="T005B-01-plato-republic-ocr")
    parser.add_argument(
        "--citation",
        default="柏拉图《理想国》，郭斌和、张竹明译，商务印书馆1986（扫描本，OCR）",
    )
    args = parser.parse_args(argv)

    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    query = args.query_file.read_text(encoding="utf-8").strip()
    summary = run(
        pdf_path=args.pdf,
        ocr_cache=args.ocr_cache,
        metadata=metadata,
        query=query,
        out_dir=args.out_dir,
        dpi=args.dpi,
        k=args.k,
        settings_path=args.settings,
        docname=args.docname,
        citation=args.citation,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

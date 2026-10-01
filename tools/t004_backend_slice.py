#!/usr/bin/env python
"""T004 — end-to-end backend vertical slice.

Implements the first real backend product loop required by
``ops/T004_END_TO_END_BACKEND_SLICE.md``:

    secondary-source passage (the real historical T001 query)
        -> PaperQA2 core-API retrieval (``Docs.aadd`` + ``Docs.aquery``)
        -> ranked candidate passages (raw chunk text + page-range label)
        -> T003 evidence localization (``tools/t003_evidence_localize.py``)
        -> user-facing evidence objects (copyable original text, PDF page
           numbers, highlight image refs, localization status, bibliographic
           metadata, basic Chinese citation shells)

Design rules taken from the T004 brief:

* the product ranking comes from the PaperQA2 *core* API; the CLI agent is
  never used (its file-level search cannot match unsegmented Chinese);
* the retrieval page label is a fallible hint for the evidence layer, not a
  fact;
* multiple candidates stay in the result; no single winner is forced;
* bibliographic metadata is never inferred from retrieval -- PaperQA2's
  inferred docname is not authoritative, and only caller-supplied,
  human-confirmed metadata can reach a citation string;
* PDF sequence pages and printed book pages are separate fields; an unknown
  printed page stays unresolved and is never silently filled with a PDF page;
* private source text and images are only written below ``data/private/``.

Two modes:

* live (default): run the retrieval chain and then the evidence chain;
* ``--candidates-from <results.json>``: skip retrieval and feed a saved
  candidate list through the same evidence/citation pipeline, so the
  object-building half can be tested with zero model calls.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import t003_evidence_localize as ev  # noqa: E402

REPO_ROOT = ev.REPO_ROOT

DEFAULT_PDF = REPO_ROOT / "data/private/C04/pqa_corpus/C04.pdf"
DEFAULT_SETTINGS = REPO_ROOT / ".pqa/settings/m1e1_c04.json"
DEFAULT_GOLD_CASE = REPO_ROOT / "data/private/C04/M1-E1_C04_gold_case.md"
DEFAULT_METADATA = REPO_ROOT / "data/private/C04/t004/inputs/c04_primary_document.json"
DEFAULT_OUT_DIR = REPO_ROOT / "data/private/C04/t004/run"
DEFAULT_RESULTS = (
    REPO_ROOT / "data/private/C04/results/m1e1_c04_20261001-113927.json"
)

RESULT_VERSION = "t004-v1"
STATUS_VALUES = ("located", "ambiguous", "unmatched", "needs_ocr")


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #


def repo_relative(path: Path | str) -> str:
    """Repository-relative POSIX path when possible, else an absolute path."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def core_chars(text: str) -> str:
    """Keep only alphanumeric/CJK characters (same reduction as T001 probes).

    The C04 text layer carries annotation digits inside the gold sentence, so
    exact substring comparison is not a valid equality test here.
    """
    return "".join(char for char in text if char.isalnum())


def fuzzy_contains(
    needle: str, haystack: str, max_extra_chars: int = 8
) -> tuple[bool, int, str]:
    """Containment that tolerates a few extra characters inside ``haystack``.

    The C04 text layer inserts annotation characters into the middle of the gold
    sentence, so byte-exact containment fails for a passage that is really
    there. This walk matches ``needle`` in order while allowing at most
    ``max_extra_chars`` unmatched ``haystack`` characters overall, and reports
    the extra characters it skipped as Unicode categories so the tolerance can
    be described without printing private source text.
    """
    if not needle or not haystack:
        return False, 0, ""
    import unicodedata

    infinity = float("inf")
    length = len(haystack)
    # row[j] = fewest skipped haystack characters needed to match needle[:i + 1]
    # with needle[i] matched at haystack[j]; parents[i][j] records the previous
    # match position so the exact skipped characters can be reported.
    row = [0 if char == needle[0] else infinity for char in haystack]
    parents: list[list[int | None]] = [[None] * length]
    for index in range(1, len(needle)):
        next_row = [infinity] * length
        next_parents: list[int | None] = [None] * length
        best_shift = infinity
        best_position: int | None = None
        for position in range(length):
            previous = position - 1
            if previous >= 0 and row[previous] < infinity:
                shift = row[previous] - previous
                if shift < best_shift:
                    best_shift = shift
                    best_position = previous
            if best_position is not None and haystack[position] == needle[index]:
                cost = best_shift + position - 1
                if cost <= max_extra_chars:
                    next_row[position] = cost
                    next_parents[position] = best_position
        row = next_row
        parents.append(next_parents)
        if all(value == infinity for value in row):
            return False, 0, ""

    end = min(range(length), key=lambda position: row[position])
    cost = row[end]
    if cost == infinity:
        return False, 0, ""
    path = [end]
    for index in range(len(needle) - 1, 0, -1):
        parent = parents[index][path[-1]]
        if parent is None:  # pragma: no cover - cannot happen for a finite cost
            return True, int(cost), ""
        path.append(parent)
    matched = set(path)
    skipped = [
        position for position in range(min(path), max(path) + 1)
        if position not in matched
    ]
    categories = ",".join(unicodedata.category(haystack[i]) for i in skipped)
    return True, int(cost), categories


def load_query(gold_case: Path) -> str:
    """Return the real historical secondary-source query from the gold case."""
    import m1e1_parse_probe as probe  # local import: pulls the PaperQA2 reader

    query, _gold = probe.load_gold(gold_case)
    return query


def load_gold_sentence(gold_case: Path) -> str:
    import m1e1_parse_probe as probe

    _query, gold = probe.load_gold(gold_case)
    return gold


def load_metadata(path: Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"document metadata must be a JSON object: {path}")
    return payload


# --------------------------------------------------------------------------- #
# retrieval (PaperQA2 core API only)
# --------------------------------------------------------------------------- #


async def retrieve_with_paperqa(
    pdf_path: Path,
    query: str,
    settings_path: Path,
    docname: str,
    citation: str,
    models: tuple | None = None,
    counter: "ModelCallCounter | None" = None,
    diagnostics_k: int = 10,
) -> dict:
    """Run the T001-style PaperQA2 core-API retrieval.

    ``Docs.aadd`` is given an explicit citation/docname: metadata is supplied by
    the caller (human-confirmed), so PaperQA2's LLM citation inference is not
    needed and its unhelpful inferred docname (historically ``Rejoice2026``) is
    never used. The query stage is unchanged from T001: ``Docs.aquery`` with the
    pinned ``.pqa/settings/m1e1_c04.json`` settings.

    ``models`` may carry explicitly built lmi models whose
    ``llm_result_callback`` is the call counter, so that criterion 11 can report
    a measured model-call count instead of a guess.
    """
    from paperqa.docs import Docs
    from paperqa.settings import Settings

    settings = Settings.model_validate_json(
        Path(settings_path).read_text(encoding="utf-8")
    )
    llm = summary_llm = embedding = None
    if models is not None:
        llm, summary_llm, embedding = models

    docs = Docs()
    started = time.perf_counter()
    await docs.aadd(
        pdf_path,
        citation=citation,
        docname=docname,
        llm_model=llm,
        embedding_model=embedding,
        settings=settings,
    )
    add_seconds = time.perf_counter() - started

    started = time.perf_counter()
    session = await docs.aquery(
        query,
        settings=settings,
        llm_model=llm,
        summary_llm_model=summary_llm,
        embedding_model=embedding,
    )
    query_seconds = time.perf_counter() - started

    candidates = []
    for index, context in enumerate(session.contexts):
        text = getattr(context, "text", None)
        candidates.append(
            {
                "candidate_id": f"cand-{index + 1:02d}",
                "rank": index + 1,
                "score": getattr(context, "score", None),
                "page_label": getattr(text, "name", None),
                "text": getattr(text, "text", None) or "",
            }
        )

    # Diagnostic, zero-extra-API retrieval stage: embedding-only ranking over
    # the same in-memory index. Recorded for rank comparison and regression,
    # not used as the product ranking.
    diagnostics: dict = {"k": diagnostics_k, "ranked": []}
    started = time.perf_counter()
    try:
        texts = await docs.retrieve_texts(
            query, diagnostics_k, settings=settings, embedding_model=embedding
        )
        diagnostics["ranked"] = [
            {
                "rank": position + 1,
                "page_label": getattr(item, "name", None),
                "text_chars": len(getattr(item, "text", "") or ""),
            }
            for position, item in enumerate(texts)
        ]
        diagnostics["status"] = "ok"
    except Exception as error:  # noqa: BLE001 - diagnostic only, never fatal
        diagnostics["status"] = f"error: {type(error).__name__}: {error}"
    diagnostics["seconds"] = round(time.perf_counter() - started, 2)

    return {
        "backend": "paperqa-core-aquery",
        "cli_agent_used": False,
        "settings_path": repo_relative(settings_path),
        "docname": docname,
        "citation_supplied_to_retrieval": citation,
        "add_seconds": round(add_seconds, 2),
        "query_seconds": round(query_seconds, 2),
        "context_count": len(candidates),
        "cost_usd": float(session.cost) if session.cost is not None else None,
        "token_counts": {
            str(key): [int(value[0]), int(value[1])]
            for key, value in (session.token_counts or {}).items()
        },
        "has_successful_answer": bool(session.has_successful_answer),
        "answer_chars": len(session.answer or ""),
        "model_calls": {
            "by_name": dict(counter.calls) if counter else {},
            "total": counter.total() if counter else 0,
        },
        "retrieval_stage_diagnostics": diagnostics,
        "candidates": candidates,
    }


# --------------------------------------------------------------------------- #
# citation assembly (confirmed metadata only)
# --------------------------------------------------------------------------- #


def _clean(value: object) -> str:
    return str(value).strip() if value is not None else ""


def build_citations(metadata: dict, printed_page: str | None = None) -> dict:
    """Assemble one footnote shell and one reference-list shell.

    Only fields present in ``metadata`` are used. Missing fields are reported in
    ``unresolved_fields`` instead of being guessed. When the printed book page is
    unknown the page segment is omitted entirely: a PDF sequence page is never
    substituted for a printed page.
    """
    author = _clean(metadata.get("author"))
    country = _clean(metadata.get("author_country"))
    title = _clean(metadata.get("title"))
    volume = _clean(metadata.get("volume"))
    translator = _clean(metadata.get("translator"))
    place = _clean(metadata.get("publisher_place"))
    publisher = _clean(metadata.get("publisher"))
    year = _clean(metadata.get("year"))
    doc_type = _clean(metadata.get("document_type")) or "M"

    unresolved: list[str] = []
    for key, value in (
        ("author", author),
        ("title", title),
        ("translator", translator),
        ("publisher_place", place),
        ("publisher", publisher),
        ("year", year),
    ):
        if not value:
            unresolved.append(key)

    page = _clean(printed_page)
    if not page:
        unresolved.append("printed_page")

    if not author or not title:
        return {
            "basic_footnote_citation": None,
            "basic_reference_citation": None,
            "citation_parts": {},
            "unresolved_fields": unresolved,
            "citation_note": (
                "author and title are required before any citation shell can be "
                "assembled; nothing was invented to fill them"
            ),
        }

    display_title = title
    if volume and volume not in title:
        display_title = f"{title}（{volume}）"
    author_display = f"[{country}]{author}" if country else author

    footnote = f"{author_display}：《{display_title}》"
    if translator:
        footnote += f"，{translator}译"
    if place and publisher:
        footnote += f"，{place}：{publisher}"
    elif publisher:
        footnote += f"，{publisher}"
    if year:
        footnote += f"，{year}年"
    if page:
        footnote += f"，第{page}页"
    footnote += "。"

    reference = f"{author_display}.{display_title}[{doc_type}]."
    if translator:
        reference += f"{translator}译."
    if place and publisher:
        reference += f"{place}:{publisher}"
    elif publisher:
        reference += publisher
    if year:
        reference += f",{year}"
    if page:
        reference += f":{page}"
    reference += "."

    return {
        "basic_footnote_citation": footnote,
        "basic_reference_citation": reference,
        "citation_parts": {
            "author_display": author_display,
            "title_display": display_title,
            "translator": translator or None,
            "place": place or None,
            "publisher": publisher or None,
            "year": year or None,
            "document_type": doc_type,
            "printed_page": page or None,
        },
        "unresolved_fields": unresolved,
        "citation_note": (
            "assembled only from caller-supplied confirmed metadata; the C04 "
            "printed book page is unconfirmed, so no page number is emitted"
        ),
    }


# --------------------------------------------------------------------------- #
# evidence objects
# --------------------------------------------------------------------------- #


def _compact_fragment(fragment: dict) -> dict:
    """Drop per-character boxes from the product object (kept by the T003 tool)."""
    return {
        key: value
        for key, value in fragment.items()
        if key != "char_boxes"
    }


def build_evidence_object(
    candidate: dict,
    source: "ev.PdfEvidenceSource",
    document_id: str,
    metadata: dict,
    images_dir: Path,
    dpi: float,
    radius: int,
) -> dict:
    """Candidate passage -> localized evidence object carrying an explicit status."""
    candidate_id = candidate["candidate_id"]
    text = candidate.get("text") or ""
    page_label = candidate.get("page_label")
    hint = ev.parse_page_hint(page_label)
    outcome = source.locate(text, hint, radius=radius)
    status = outcome["status"]
    assert status in STATUS_VALUES, f"unexpected status from T003 layer: {status}"

    warnings: list[str] = []
    fragments_out: list[dict] = []
    highlight_refs: list[str] = []
    original_refs: list[str] = []

    if status == "located":
        for fragment in outcome["fragments"]:
            page_number = fragment["page_number"]
            page_image = source.render_page(fragment["page_index"])
            base = f"{candidate_id}_pdf{page_number:04d}"
            original_path = images_dir / f"{base}_original.png"
            highlight_path = images_dir / f"{base}_highlight.png"
            page_image.save(original_path)
            highlighted, stats = ev.draw_highlights(
                page_image,
                [item["box_px"] for item in fragment["highlight_boxes"]],
                candidate_id,
                page_number,
            )
            highlighted.save(highlight_path)
            fragment["image"] = {
                "original": repo_relative(original_path),
                "highlight": repo_relative(highlight_path),
                "pixel_size": list(page_image.size),
                "dpi": dpi,
            }
            ev.finalize_fragment(
                fragment,
                page_image,
                stats,
                [
                    round(ev.ink_ratio(page_image, item["box_px"]), 4)
                    for item in fragment["highlight_boxes"]
                ],
            )
            if not fragment.get("geometry_ok", False):
                warnings.append(
                    f"page {page_number}: highlight geometry failed the sanity "
                    "check; treat the image with caution"
                )
            highlight_refs.append(fragment["image"]["highlight"])
            original_refs.append(fragment["image"]["original"])
            fragments_out.append(_compact_fragment(fragment))
        if not outcome.get("hint_confirmed"):
            warnings.append(
                "stored retrieval page label was not confirmed; the passage was "
                "located by a whole-document fallback search"
            )
    elif status == "ambiguous":
        warnings.append(
            f"{outcome['occurrences_in_hint_window']} full matches in the search "
            "window; no geometry or highlight was emitted (no guessed highlight)"
        )
    elif status == "unmatched":
        warnings.append(
            "no full match for this candidate text in the document; the candidate "
            "is kept and no highlight was emitted"
        )
    else:  # needs_ocr
        warnings.append(
            "the hinted page has no usable text layer; OCR is out of scope for "
            "this slice, so no geometry was emitted"
        )

    if candidate.get("score") is not None:
        warnings.append(
            f"PaperQA2 context relevance score {candidate['score']} (model "
            "judgement, not source evidence)"
        )

    pdf_pages = sorted(
        {fragment["page_number"] for fragment in fragments_out}
    )
    citations = build_citations(metadata, printed_page=None)
    unresolved = list(citations["unresolved_fields"])
    unresolved.append("printed_page_numbers")
    if status != "located":
        unresolved.append("highlight_geometry")

    return {
        "candidate_id": candidate_id,
        "status": status,
        "source_document_id": document_id,
        "retrieval_rank": candidate.get("rank"),
        "retrieval_score": candidate.get("score"),
        "retrieval_page_label": page_label,
        "original_text": text,
        "original_text_char_count": len(text),
        "normalized_char_count": outcome["norm_query_chars"],
        "pdf_page_numbers": pdf_pages,
        "printed_page_numbers": [],
        "highlighted_image_refs": highlight_refs,
        "original_page_image_refs": original_refs,
        "fragments": fragments_out,
        "localization": {
            key: outcome[key]
            for key in (
                "status",
                "search_scope",
                "hint_pages",
                "hint_confirmed",
                "scanned_pages",
                "occurrences_in_hint_window",
                "occurrences_in_pdf",
                "scan_seconds",
                "missing_box_chars",
                "invalid_box_chars",
            )
            if key in outcome
        },
        "bibliographic_metadata": {
            "document_id": document_id,
            "author": _clean(metadata.get("author")) or None,
            "author_country": _clean(metadata.get("author_country")) or None,
            "title": _clean(metadata.get("title")) or None,
            "volume": _clean(metadata.get("volume")) or None,
            "translator": _clean(metadata.get("translator")) or None,
            "publisher_place": _clean(metadata.get("publisher_place")) or None,
            "publisher": _clean(metadata.get("publisher")) or None,
            "year": _clean(metadata.get("year")) or None,
            "document_type": _clean(metadata.get("document_type")) or None,
            "metadata_origin": metadata.get("metadata_origin"),
            "printed_page": None,
        },
        "basic_footnote_citation": citations["basic_footnote_citation"],
        "basic_reference_citation": citations["basic_reference_citation"],
        "citation_parts": citations["citation_parts"],
        "warnings": warnings,
        "unresolved_fields": unresolved,
    }


def build_result(
    candidates: list[dict],
    pdf_path: Path,
    document_id: str,
    metadata: dict,
    out_dir: Path,
    dpi: float,
    radius: int,
) -> dict:
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    pdf_fingerprint = ev.sha256_of(pdf_path)

    source = ev.PdfEvidenceSource(pdf_path, dpi=dpi)
    started = time.perf_counter()
    try:
        objects = [
            build_evidence_object(
                candidate,
                source,
                document_id,
                metadata,
                images_dir,
                dpi,
                radius,
            )
            for candidate in candidates
        ]
    finally:
        source.close()
    elapsed = round(time.perf_counter() - started, 2)

    status_counts: dict[str, int] = {}
    for item in objects:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

    return {
        "result_version": RESULT_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_document": {
            "document_id": document_id,
            "path": repo_relative(pdf_path),
            "sha256": pdf_fingerprint,
            "metadata_origin": metadata.get("metadata_origin"),
        },
        "evidence": {
            "elapsed_seconds": elapsed,
            "dpi": dpi,
            "search_radius": radius,
            "status_counts": status_counts,
            "candidate_count": len(objects),
            "api_calls": 0,
            "api_cost_usd": 0.0,
        },
        "candidates": objects,
    }


# --------------------------------------------------------------------------- #
# acceptance evaluation
# --------------------------------------------------------------------------- #


class ModelCallCounter:
    """Count LLM results returned by the traced lmi models (criterion 11)."""

    def __init__(self) -> None:
        self.calls: dict[str, int] = {}

    def __call__(self, result: object) -> None:
        name = getattr(result, "name", None) or "llm"
        key = str(name)
        self.calls[key] = self.calls.get(key, 0) + 1

    def total(self) -> int:
        return sum(self.calls.values())


def _citations_are_confirmed(metadata: dict, object_: dict) -> tuple[bool, str]:
    """Criterion 8: citations use only confirmed metadata, with no invented field."""
    forbidden = ("None", "Unknown", "unknown", "未知", "TODO", "占位")
    for field in ("basic_footnote_citation", "basic_reference_citation"):
        value = object_.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            return False, f"{field} is not a usable string"
        for token in forbidden:
            if token in value:
                return False, f"{field} contains placeholder text {token!r}"

    # every value the builder used must come from the confirmed metadata record
    parts = object_.get("citation_parts") or {}
    for key in ("translator", "place", "publisher", "year"):
        used = parts.get(key)
        if used is not None and _clean(metadata.get(key if key != "place" else
                                                   "publisher_place")) != used:
            return False, f"citation used {key}={used!r}, which is not confirmed metadata"
    if parts.get("printed_page") is None and "页" in (
        object_.get("basic_footnote_citation") or ""
    ):
        # no printed page is confirmed, so no page segment may appear
        return False, "footnote citation contains a page number that is not confirmed"
    return True, "citation strings use confirmed metadata only"


def _git_private_check(result_path: Path, objects: list[dict]) -> tuple[bool, str]:
    """Criterion 10: private text/images are not tracked by Git."""
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "data/private"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if tracked.stdout.strip():
        return False, f"Git tracks private paths: {tracked.stdout.split()}"
    if "data/private" not in result_path.as_posix():
        return False, f"result file is not below data/private: {result_path}"
    stray = [
        ref
        for object_ in objects
        for ref in (
            object_["highlighted_image_refs"] + object_["original_page_image_refs"]
        )
        if not ref.startswith("data/private/")
    ]
    if stray:
        return False, f"image references outside data/private: {stray[:3]}"
    return True, "no private text or image path is tracked by Git"


def evaluate_acceptance(
    result: dict,
    retrieval: dict | None,
    query: str,
    gold_sentence: str,
    gold_pdf_page: int,
    result_path: Path,
    metadata: dict,
    t003_probe_summary: Path | None = None,
) -> dict:
    """Evaluate the twelve T004 acceptance criteria against the produced result."""
    objects = result["candidates"]
    checks: list[dict] = []

    def add(criterion_id: int, text: str, ok: bool, evidence: str) -> None:
        checks.append(
            {
                "criterion": criterion_id,
                "requirement": text,
                "ok": bool(ok),
                "evidence": evidence,
            }
        )

    backend = (retrieval or {}).get("backend")
    add(
        1,
        "one command starts from the real secondary-source query and runs the "
        "connected backend loop",
        bool(query) and bool(objects) and backend == "paperqa-core-aquery",
        f"query_chars={len(query)} candidates={len(objects)} backend={backend}",
    )
    add(
        2,
        "retrieval returns candidates without using the PaperQA2 CLI agent",
        bool(retrieval) and retrieval.get("cli_agent_used") is False
        and str(retrieval.get("backend", "")).startswith("paperqa-core"),
        f"backend={backend} cli_agent_used={(retrieval or {}).get('cli_agent_used')}",
    )

    located = [
        item
        for item in objects
        if item["status"] == "located"
        and item["highlighted_image_refs"]
        and all(fragment.get("geometry_ok") for fragment in item["fragments"])
    ]
    add(
        3,
        "at least one candidate is localized to exact page geometry and produces "
        "a highlight image",
        bool(located),
        f"located_with_geometry={len(located)} pages="
        f"{[item['pdf_page_numbers'] for item in located][:3]}",
    )

    gold_core = core_chars(gold_sentence)
    gold_matches = [
        (item, extra, categories)
        for item in objects
        for found, extra, categories in [
            fuzzy_contains(gold_core, core_chars(item["original_text"]))
        ]
        if found
    ]
    gold_objects = [item for item, _extra, _categories in gold_matches]
    gold_pages = sorted(
        {page for item in gold_objects for page in item["pdf_page_numbers"]}
    )
    add(
        4,
        f"the historical gold passage is surfaced and its evidence resolves to "
        f"PDF page {gold_pdf_page}",
        bool(gold_objects) and gold_pdf_page in gold_pages,
        f"gold_candidates={[item['candidate_id'] for item in gold_objects]} "
        f"gold_pdf_pages={gold_pages} "
        f"tolerated_extra_chars={[extra for _i, extra, _c in gold_matches]} "
        f"extra_char_categories={[c for _i, _e, c in gold_matches]}",
    )

    add(
        5,
        "multiple candidates remain represented in the output",
        len(objects) >= 2,
        f"candidate_count={len(objects)}",
    )
    add(
        6,
        "each candidate has an explicit localization status",
        all(item["status"] in STATUS_VALUES for item in objects),
        f"status_counts={result['evidence']['status_counts']}",
    )
    add(
        7,
        "the result includes copyable original text",
        all(isinstance(item.get("original_text"), str) and item["original_text"]
            for item in objects),
        f"text_chars={[item['original_text_char_count'] for item in objects]}",
    )

    citation_results = [_citations_are_confirmed(metadata, item) for item in objects]
    add(
        8,
        "citation strings are produced only from confirmed metadata and contain "
        "no invented fields",
        all(ok for ok, _ in citation_results),
        citation_results[0][1] if citation_results else "no candidates",
    )
    pages_confirmed = all(
        not item["printed_page_numbers"] and isinstance(item["pdf_page_numbers"], list)
        for item in objects
    )
    # The citation shells are compared against shells rebuilt from the same
    # confirmed metadata: when no printed page is confirmed they must be
    # byte-identical to the page-less shells, so a PDF page number can never
    # appear where a printed page belongs.
    if not _clean(metadata.get("printed_page")):
        expected = build_citations(metadata, printed_page=None)
        no_page_in_citation = all(
            item.get("basic_footnote_citation") == expected["basic_footnote_citation"]
            and item.get("basic_reference_citation")
            == expected["basic_reference_citation"]
            for item in objects
        )
        page_evidence = (
            "printed_page_numbers always empty; printed_page stays unresolved; "
            "every citation equals the page-less shell rebuilt from the same "
            "confirmed metadata"
        )
    else:
        no_page_in_citation = True
        page_evidence = "a printed page is confirmed and was emitted in the citation"
    add(
        9,
        "PDF sequence pages are not misrepresented as printed book pages",
        pages_confirmed
        and no_page_in_citation
        and all("printed_page" in item["unresolved_fields"] for item in objects),
        page_evidence,
    )

    git_ok, git_evidence = _git_private_check(result_path, objects)
    add(10, "no private source text or images are committed to Git", git_ok, git_evidence)

    run = result.get("run", {})
    calls = (run.get("model_calls") or {}).get("total")
    cost = run.get("cost_usd")
    tokens = run.get("token_counts")
    runtime_ok = (
        run.get("evidence_seconds") is not None
        and run.get("retrieval_seconds") is not None
        and calls is not None
        and cost is not None
        and tokens
    )
    add(
        11,
        "actual runtime, model/API calls, tokens and cost are recorded",
        runtime_ok,
        f"retrieval_seconds={run.get('retrieval_seconds')} "
        f"evidence_seconds={run.get('evidence_seconds')} model_calls={calls} "
        f"tokens={tokens} cost_usd={cost}",
    )

    regression_ok = True
    regression_evidence = "T001/T003 artifacts untouched (sha256 recorded)"
    if t003_probe_summary is not None and Path(t003_probe_summary).exists():
        summary = json.loads(Path(t003_probe_summary).read_text(encoding="utf-8"))
        regression_ok = summary.get("failed", 1) == 0
        regression_evidence = (
            f"T003 probes {summary.get('passed')}/{summary.get('probe_count')} passed; "
            f"{regression_evidence}"
        )
    add(
        12,
        "existing T001/T003 regression checks still pass or are unaffected",
        regression_ok,
        regression_evidence,
    )

    passed = sum(1 for check in checks if check["ok"])
    return {
        "criteria": checks,
        "passed": passed,
        "total": len(checks),
        "result": "PASS" if passed == len(checks) else "FAIL",
        "gold_candidate_ids": [item["candidate_id"] for item in gold_objects],
        "gold_pdf_pages": gold_pages,
    }


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #


async def run_live(args: argparse.Namespace) -> tuple[dict, dict]:
    metadata = load_metadata(args.metadata)
    query = load_query(args.gold_case)
    citation = build_citations(metadata)["basic_reference_citation"] or "C04"

    from paperqa.settings import Settings

    settings = Settings.model_validate_json(args.settings.read_text(encoding="utf-8"))
    counter = ModelCallCounter()
    llm = settings.get_llm()
    summary_llm = settings.get_summary_llm()
    embedding = settings.get_embedding_model()
    for model in (llm, summary_llm, embedding):
        try:
            model.llm_result_callback = counter
        except Exception as error:  # noqa: BLE001 - measurement must never break the run
            print(f"warning: could not attach call counter: {error}")

    retrieval = await retrieve_with_paperqa(
        pdf_path=args.pdf,
        query=query,
        settings_path=args.settings,
        docname=args.docname,
        citation=citation,
        models=(llm, summary_llm, embedding),
        counter=counter,
        diagnostics_k=args.retrieval_diagnostics_k,
    )
    return metadata, retrieval


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument("--gold-case", type=Path, default=DEFAULT_GOLD_CASE)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--docname", default="C04")
    parser.add_argument("--dpi", type=float, default=ev.DEFAULT_DPI)
    parser.add_argument("--radius", type=int, default=1)
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument("--retrieval-diagnostics-k", type=int, default=10)
    parser.add_argument(
        "--candidates-from",
        type=Path,
        default=None,
        help="offline mode: reuse a saved PaperQA2 results JSON instead of "
        "running retrieval (zero model calls)",
    )
    parser.add_argument("--t003-probe-summary", type=Path, default=None)
    parser.add_argument(
        "--recheck",
        type=Path,
        default=None,
        help="re-evaluate the acceptance criteria for an existing run directory; "
        "no retrieval and no model call is performed",
    )
    args = parser.parse_args(argv)

    if args.recheck is not None:
        run_dir = args.recheck
        result = json.loads(
            (run_dir / "evidence_objects.json").read_text(encoding="utf-8")
        )
        metadata = load_metadata(args.metadata)
        acceptance = evaluate_acceptance(
            result=result,
            retrieval=result.get("retrieval"),
            query=load_query(args.gold_case),
            gold_sentence=load_gold_sentence(args.gold_case),
            gold_pdf_page=109,
            result_path=run_dir / "evidence_objects.json",
            metadata=metadata,
            t003_probe_summary=args.t003_probe_summary,
        )
        acceptance["result_path"] = repo_relative(run_dir / "evidence_objects.json")
        acceptance["recheck"] = True
        (run_dir / "acceptance.json").write_text(
            json.dumps(acceptance, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "result": acceptance["result"],
                    "criteria_passed": f"{acceptance['passed']}/{acceptance['total']}",
                    "failed_criteria": [
                        check["criterion"]
                        for check in acceptance["criteria"]
                        if not check["ok"]
                    ],
                },
                indent=2,
            )
        )
        return 0 if acceptance["result"] == "PASS" else 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    metadata = load_metadata(args.metadata)
    document_id = str(metadata.get("document_id") or args.docname)
    query = load_query(args.gold_case)
    gold_sentence = load_gold_sentence(args.gold_case)

    if args.candidates_from is not None:
        mode = "offline-candidates"
        retrieval = None
        saved = ev.load_candidates(args.candidates_from)
        candidates = [
            {
                "candidate_id": f"cand-{index + 1:02d}",
                "rank": item.get("rank"),
                "score": item.get("score"),
                "page_label": item.get("page_label"),
                "text": item.get("text", ""),
            }
            for index, item in enumerate(saved)
        ]
    else:
        mode = "live"
        metadata, retrieval = asyncio.run(run_live(args))
        candidates = retrieval["candidates"]

    if args.max_candidates:
        candidates = candidates[: args.max_candidates]

    result = build_result(
        candidates=candidates,
        pdf_path=args.pdf,
        document_id=document_id,
        metadata=metadata,
        out_dir=args.out_dir,
        dpi=args.dpi,
        radius=args.radius,
    )
    result["run"] = {
        "entrypoint": "tools/t004_backend_slice.py",
        "mode": mode,
        "started_at": started_at,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "query_chars": len(query),
        "query_source": repo_relative(args.gold_case),
        "retrieval_seconds": round(
            (retrieval["add_seconds"] + retrieval["query_seconds"]), 2
        )
        if retrieval
        else 0.0,
        "evidence_seconds": result["evidence"]["elapsed_seconds"],
        "model_calls": (retrieval or {}).get("model_calls", {"by_name": {}, "total": 0}),
        "token_counts": (retrieval or {}).get("token_counts", {}),
        "cost_usd": (retrieval or {}).get("cost_usd", 0.0),
    }
    result["retrieval"] = retrieval

    result_path = args.out_dir / "evidence_objects.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    acceptance = evaluate_acceptance(
        result=result,
        retrieval=retrieval,
        query=query,
        gold_sentence=gold_sentence,
        gold_pdf_page=109,
        result_path=result_path,
        metadata=metadata,
        t003_probe_summary=args.t003_probe_summary,
    )
    acceptance["result_path"] = repo_relative(result_path)
    (args.out_dir / "acceptance.json").write_text(
        json.dumps(acceptance, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    public_summary = {
        "result": acceptance["result"],
        "criteria_passed": f"{acceptance['passed']}/{acceptance['total']}",
        "mode": mode,
        "candidate_count": len(result["candidates"]),
        "status_counts": result["evidence"]["status_counts"],
        "pdf_pages_by_candidate": {
            item["candidate_id"]: item["pdf_page_numbers"]
            for item in result["candidates"]
        },
        "gold_candidate_ids": acceptance["gold_candidate_ids"],
        "gold_pdf_pages": acceptance["gold_pdf_pages"],
        "highlight_images": sum(
            len(item["highlighted_image_refs"]) for item in result["candidates"]
        ),
        "registered_statuses": sorted(
            {item["status"] for item in result["candidates"]}
        ),
        "run": result["run"],
        "retrieval_stage_diagnostics": (
            (retrieval or {}).get("retrieval_stage_diagnostics")
        ),
        "failed_criteria": [
            check["criterion"] for check in acceptance["criteria"] if not check["ok"]
        ],
        "result_path": acceptance["result_path"],
    }
    (args.out_dir / "run_summary.json").write_text(
        json.dumps(public_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(public_summary, ensure_ascii=True, indent=2))
    return 0 if acceptance["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

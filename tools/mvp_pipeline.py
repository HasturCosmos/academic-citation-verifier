#!/usr/bin/env python
"""Canonical MVP pipeline for 二流文科生的二手文献引用助手.

This module is the single backend contract behind the product entry point
(``tools/mvp_app.py``). It replaces "run one of the T00x experiment scripts" with
one route function that both supported source kinds share:

    secondary-source passage (+ fallible hints)
        -> resolve a primary-source resource (local, registered or explicit)
        -> decide how the source can be searched at all
             * PDF with a usable text layer -> the accepted text-layer path
             * image-only scan + OCR cache    -> the adopted RapidOCR fallback
             * neither                        -> honest insufficient-source state
        -> chunk with the upstream PaperQA2 chunker (same page-range labels)
        -> rank with the pinned *local* embedding (no LLM, no paid call)
        -> localize each ranked passage with the proven T003/T004 evidence layer
        -> explicit per-candidate status + a four-way product result state

Design rules carried over from T003/T004/T005B/T006 and PRODUCT_V0_1:

* the secondary passage is the query, never the evidence;
* PDF sequence pages and printed book pages are separate fields; an unknown
  printed page stays unresolved and is never silently replaced;
* citations are assembled only from caller-confirmed metadata;
* OCR text is a machine reading of a page image and always says so;
* no quotation, page number or highlight is invented when localization fails;
* private text and page images are only ever written below ``data/private/``.

Retrieval modes:

* ``local`` (default): embedding-only ranking over the upstream index. Zero
  model calls, $0.00, no network; deterministic for a given environment.
* ``llm``: the accepted T004 PaperQA2 ``Docs.aquery`` path (LLM evidence
  reranking). Needs a provider key and spends money, so it is opt-in.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import t003_evidence_localize as ev  # noqa: E402
import t004_backend_slice as t004  # noqa: E402
import t005b_scan_probe as scan_probe  # noqa: E402
import t006_ocr_evidence as oe  # noqa: E402

DEFAULT_SETTINGS = REPO_ROOT / ".pqa/settings/m1e1_c04.json"
DEFAULT_SOURCES = TOOLS_DIR / "mvp_sources.json"
DEFAULT_RUNS_DIR = REPO_ROOT / "data/private/mvp_runs"
DEFAULT_UPLOADS_DIR = REPO_ROOT / "data/private/mvp_uploads"
DEFAULT_CACHE_DIR = REPO_ROOT / "data/private/mvp_cache"

RESULT_VERSION = "mvp-candidate-v1"

# The four product result states required by PRODUCT_V0_1. They are never
# collapsed into a generic "not found".
STATE_EVIDENCE_FOUND = "evidence_found"
STATE_MULTIPLE_CANDIDATES = "multiple_candidates"
STATE_NO_CORRESPONDING_PASSAGE = "no_corresponding_passage"
STATE_INSUFFICIENT_SOURCE = "insufficient_source"
RESULT_STATES = (
    STATE_EVIDENCE_FOUND,
    STATE_MULTIPLE_CANDIDATES,
    STATE_NO_CORRESPONDING_PASSAGE,
    STATE_INSUFFICIENT_SOURCE,
)

# A ranked passage counts as a *plausible* candidate when its retrieval
# distance is inside this relative band of the best hit. The rule is
# deliberately simple, documented and visible in the output: it decides only
# how many alternatives the product offers, never which one is "correct".
PLAUSIBLE_BAND = 0.15

OCR_WARNING = (
    "该段文字由 RapidOCR 从扫描页图像识别得到，不是出版社文本层；"
    "引用前必须与页面图像逐字核对。"
)
OCR_UNRESOLVED_FIELD = "ocr_text_verification"


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #


def repo_relative(path: Path | str) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _offline_model_env() -> None:
    """Keep local-model lookups offline by default.

    The pinned embedding model is already in the local Hugging Face cache, so the
    default product run must not need the network. ``MVP_ALLOW_MODEL_DOWNLOAD=1``
    restores the online behaviour for a machine that has to fetch it once.
    """
    if os.environ.get("MVP_ALLOW_MODEL_DOWNLOAD") == "1":
        return
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    # LiteLLM otherwise tries to fetch its remote price map on import and prints
    # a scary network warning on a deliberately offline run.
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")


def load_settings(settings_path: Path = DEFAULT_SETTINGS):
    from paperqa.settings import Settings

    return Settings.model_validate_json(Path(settings_path).read_text(encoding="utf-8"))


def reader_config_value(config, key: str, default: int) -> int:
    """``parsing.reader_config`` is a plain dict in the pinned PaperQA2 build."""
    if config is None:
        return default
    if isinstance(config, dict):
        return int(config.get(key, default))
    return int(getattr(config, key, default))


def chunk_params(settings) -> tuple[int, int]:
    reader = settings.parsing.reader_config
    return (
        reader_config_value(reader, "chunk_chars", 400),
        reader_config_value(reader, "overlap", 100),
    )


def load_metadata(path: Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"document metadata must be a JSON object: {path}")
    return payload


# --------------------------------------------------------------------------- #
# primary-source registry
# --------------------------------------------------------------------------- #


def load_sources(path: Path = DEFAULT_SOURCES) -> list[dict]:
    """Read the local primary-source registry.

    The registry lists *local* resources the product may search. It holds paths
    and human-confirmed metadata only; no source bytes and no private text is
    committed, because everything it points at lives under ``data/private/``.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    sources = payload.get("sources") if isinstance(payload, dict) else payload
    if not isinstance(sources, list) or not sources:
        raise SystemExit(f"no sources in registry: {path}")
    return sources


def find_source(sources: list[dict], key: str) -> dict:
    for source in sources:
        if key in (source.get("source_id"), source.get("label")) or key == str(
            source.get("pdf")
        ):
            return source
    available = ", ".join(str(source.get("source_id")) for source in sources)
    raise SystemExit(f"unknown primary source {key!r}; registered: {available}")


def resolve_paths(source: dict) -> dict:
    """Turn registry strings into absolute paths plus the confirmed metadata."""
    pdf = Path(source["pdf"])
    if not pdf.is_absolute():
        pdf = REPO_ROOT / pdf
    metadata_path = Path(source["metadata"])
    if not metadata_path.is_absolute():
        metadata_path = REPO_ROOT / metadata_path
    ocr_cache = source.get("ocr_cache")
    ocr_cache_path = None
    if ocr_cache:
        ocr_cache_path = Path(ocr_cache)
        if not ocr_cache_path.is_absolute():
            ocr_cache_path = REPO_ROOT / ocr_cache_path
    return {
        "source_id": str(source.get("source_id") or pdf.stem),
        "label": str(source.get("label") or source.get("source_id") or pdf.name),
        "pdf": pdf,
        "metadata_path": metadata_path,
        "metadata": load_metadata(metadata_path) if metadata_path.exists() else {},
        "ocr_cache": ocr_cache_path,
        "docname": str(source.get("docname") or source.get("source_id") or pdf.stem),
        "citation": source.get("citation"),
        "notes": source.get("notes"),
    }


# --------------------------------------------------------------------------- #
# source searchability
# --------------------------------------------------------------------------- #


def scan_source_text_layer(pdf_path: Path) -> dict:
    """Zero-cost answer to "can this PDF be searched at all?"."""
    report = scan_probe.scan(pdf_path)
    report.pop("per_page_char_counts", None)
    report["status"] = (
        "searchable" if report["pages_with_usable_text_layer"] else "needs_ocr"
    )
    return report


def ocr_cache_report(cache_dir: Path | None) -> dict:
    if cache_dir is None or not Path(cache_dir).exists():
        return {"present": False, "pages": 0, "total_chars": 0, "pages_without_text": 0}
    pages = oe.load_cached_pages(Path(cache_dir))
    empty = sum(
        1 for record in pages.values() if record["char_count"] < ev.MIN_TEXT_LAYER_CHARS
    )
    return {
        "present": bool(pages),
        "pages": len(pages),
        "total_chars": sum(record["char_count"] for record in pages.values()),
        "pages_without_text": empty,
        "engine": next(iter(pages.values())).get("engine") if pages else None,
    }


# --------------------------------------------------------------------------- #
# index building (upstream chunker + upstream retrieval component)
# --------------------------------------------------------------------------- #


def parse_pdf_pages(pdf_path: Path, cache_dir: Path | None = DEFAULT_CACHE_DIR) -> tuple[dict[str, str], dict]:
    """Parse a text-layer PDF into ``{page_number: text}`` with a local cache."""
    digest = sha256_of(pdf_path)
    cache_path = None
    if cache_dir is not None:
        cache_path = Path(cache_dir) / "parse" / f"{digest}.json"
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            return payload["pages"], {
                "source": "cache",
                "seconds": 0.0,
                "page_count": len(payload["pages"]),
            }

    from paperqa.settings import ParsingSettings, get_default_pdf_parser

    parser = get_default_pdf_parser()
    started = time.perf_counter()
    parsed = parser(
        pdf_path,
        page_size_limit=ParsingSettings().page_size_limit,
        parse_media=False,
    )
    seconds = round(time.perf_counter() - started, 2)
    content = parsed.content
    if not isinstance(content, dict):
        raise SystemExit(f"unexpected parser output for {pdf_path}")
    pages = {
        str(page): (entry[0] if isinstance(entry, tuple) else entry)
        for page, entry in content.items()
    }
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps({"sha256": digest, "pages": pages}, ensure_ascii=False),
            encoding="utf-8",
        )
    return pages, {"source": "parsed", "seconds": seconds, "page_count": len(pages)}


def chunk_pages(pages: dict[str, str], *, docname: str, citation: str, chunk_chars: int, overlap: int) -> tuple[object, list]:
    """Chunk page text exactly like PaperQA2 chunks a parsed PDF."""
    import uuid

    from paperqa.readers import ParsedMetadata, ParsedText, chunk_pdf
    from paperqa.types import Doc

    content = {page: text for page, text in pages.items() if text}
    if not content:
        raise SystemExit("no page text to index")
    parsed_text = ParsedText(
        content=content,
        metadata=ParsedMetadata(
            parsing_libraries=["paperqa.readers (page text)"],
            total_parsed_text_length=sum(len(text) for text in content.values()),
            name=docname,
        ),
    )
    doc = Doc(dockey=str(uuid.uuid4()), docname=docname, citation=citation or docname)
    chunks = chunk_pdf(parsed_text, doc, chunk_chars=chunk_chars, overlap=overlap)
    return doc, chunks


async def index_chunks(chunks: list, doc, settings):
    from paperqa.docs import Docs

    embedding = settings.get_embedding_model()
    docs = Docs()
    ok = await docs.aadd_texts(chunks, doc=doc, settings=settings, embedding_model=embedding)
    return docs, embedding, bool(ok)


def source_cache_key(pdf_sha256: str, route: str, chunk_chars: int, overlap: int, settings, docname: str) -> tuple:
    return (pdf_sha256, route, chunk_chars, overlap, str(settings.embedding), docname)


_INDEX_CACHE: dict[tuple, tuple] = {}
_INDEX_LOCK = threading.Lock()


def build_or_get_index(chunks: list, doc, settings, cache_key: tuple):
    """Build the retrieval index once per source inside the running process.

    Embedding a long book dominates the cost of the first query, and the local
    web app is a long-running process, so a prepared index is kept in memory and
    reused for later questions about the same source. Nothing is written to disk
    and the evidence/status rules are unaffected: this only avoids recomputing
    vectors that cannot change while the pinned model and chunking stay fixed.
    """
    with _INDEX_LOCK:
        prepared = _INDEX_CACHE.get(cache_key)
    if prepared is not None:
        docs, embedding = prepared
        return docs, embedding, True, True
    docs, embedding, ok = asyncio.run(index_chunks(chunks, doc, settings))
    if ok:
        with _INDEX_LOCK:
            _INDEX_CACHE[cache_key] = (docs, embedding)
    return docs, embedding, ok, False


def _cosine(query_vector, document_vector) -> float | None:
    if document_vector is None:
        return None
    import numpy as np

    array = np.asarray(document_vector, dtype=float)
    norm = float(np.linalg.norm(array)) or 1.0
    query_norm = float(np.linalg.norm(query_vector)) or 1.0
    return round(float(np.dot(query_vector, array) / (query_norm * norm)), 4)


async def rank_candidates(docs, embedding, query: str, k: int, settings) -> list[dict]:
    """MMR retrieval plus an explicit local similarity score.

    ``Docs.retrieve_texts`` returns ``Text`` objects without a score field, so
    the product computes cosine similarity between the query embedding and each
    returned passage with the *same* pinned local model. The score exists only to
    order the displayed alternatives; it is never evidence.
    """
    import numpy as np

    matches = await docs.retrieve_texts(
        query, k=k, settings=settings, embedding_model=embedding
    )
    query_vector = np.asarray(await embedding.embed_document(query), dtype=float)
    candidates: list[dict] = []
    for rank, match in enumerate(matches, start=1):
        candidates.append(
            {
                "rank": rank,
                "score": _cosine(query_vector, getattr(match, "embedding", None)),
                "page_label": getattr(match, "name", None),
                "text": getattr(match, "text", "") or "",
            }
        )
    return candidates


async def merge_candidates(primary: list[dict], extra: list[dict], embedding, query: str) -> list[dict]:
    """Union two ranked lists, then re-rank every candidate against one query.

    Fallible hints are used to *add* candidates (recall), never to remove one
    that the plain secondary passage already produced. Scores from the two
    retrieval passes are not comparable to each other, so every candidate that
    only the hint query produced is rescored against the secondary passage and
    the merged list is sorted by that single score.
    """
    import numpy as np

    merged: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for pool, origin in ((primary, "secondary"), (extra, "hints")):
        for item in pool:
            key = (str(item.get("page_label")), str(item.get("text"))[:200])
            if key in seen:
                continue
            seen.add(key)
            candidate = dict(item)
            candidate["retrieved_with"] = origin
            merged.append(candidate)

    hint_only = [item for item in merged if item["retrieved_with"] == "hints"]
    if hint_only:
        query_vector = np.asarray(await embedding.embed_document(query), dtype=float)
        vectors = await embedding.embed_documents([item["text"] for item in hint_only])
        for item, vector in zip(hint_only, vectors):
            item["score"] = _cosine(query_vector, vector)

    merged.sort(key=lambda item: item["score"] if item["score"] is not None else -1.0, reverse=True)
    for index, candidate in enumerate(merged, start=1):
        candidate["rank"] = index
        candidate["candidate_id"] = f"cand-{index:02d}"
    return merged


# --------------------------------------------------------------------------- #
# evidence objects
# --------------------------------------------------------------------------- #


def build_evidence_objects(
    candidates: list[dict],
    source,
    *,
    metadata: dict,
    images_dir: Path,
    dpi: float,
    radius: int,
    evidence_origin: str,
) -> list[dict]:
    """Run the unchanged T004 evidence builder and stamp the evidence origin."""
    images_dir.mkdir(parents=True, exist_ok=True)
    document_id = str(metadata.get("document_id") or "unknown-document")
    objects: list[dict] = []
    for candidate in candidates:
        record = t004.build_evidence_object(
            candidate,
            source,
            document_id=document_id,
            metadata=metadata,
            images_dir=images_dir,
            dpi=dpi,
            radius=radius,
        )
        record["evidence_origin"] = evidence_origin
        record["retrieved_with"] = candidate.get("retrieved_with", "secondary")
        if evidence_origin == "ocr":
            record["warnings"] = [OCR_WARNING, *record.get("warnings", [])]
            record["unresolved_fields"] = sorted(
                set(record.get("unresolved_fields", [])) | {OCR_UNRESOLVED_FIELD}
            )
        objects.append(record)
    return objects


# --------------------------------------------------------------------------- #
# page furniture (display-only, deterministic)
# --------------------------------------------------------------------------- #


def _cjk_count(text: str) -> int:
    return sum(1 for char in text if "\u4e00" <= char <= "\u9fff")


def repeated_page_furniture(
    page_texts: dict[str, str],
    *,
    min_pages: int = 8,
    page_fraction: float = 0.02,
    max_chars: int = 6,
) -> set[str]:
    """Find repeated margin/noise tokens that may be hidden in the display text.

    The rule is deliberately narrow so it cannot delete real content. A line
    qualifies only when it is a *noise token* — at most two characters, or at
    most six characters made entirely of digits/punctuation/letters with no
    Chinese ideograph — and it appears as a whole line on at least
    ``max(min_pages, page_fraction * pages)`` distinct pages. Measured on the
    T005B-01 scan this catches the OCR fragments of the vertical running head
    (``理``/``想``/``国``), margin numerals and Latin section letters, while
    leaving repeated dialogue stamps such as ``格：是的。`` and running titles
    such as ``理想国`` / ``第十卷`` untouched: those can carry meaning, so they
    are never hidden.

    Nothing here mutates evidence: the caller may use the result to build a
    *display* string, while the retrieved ``original_text`` and the highlight
    geometry stay byte-identical.
    """
    counts: dict[str, int] = {}
    threshold = max(min_pages, round(page_fraction * len(page_texts)))
    for text in page_texts.values():
        seen_on_page = set()
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or len(stripped) > max_chars:
                continue
            if len(stripped) > 2 and _cjk_count(stripped):
                continue
            seen_on_page.add(stripped)
        for line in seen_on_page:
            counts[line] = counts.get(line, 0) + 1
    return {line for line, count in counts.items() if count >= threshold}


def display_text_for(original_text: str, furniture: set[str]) -> tuple[str, list[str]]:
    """Return display text with repeated page furniture lines removed.

    The retrieved text is untouched; this is a presentation-only reduction, and
    every removed line is reported so the UI can say what it hid.
    """
    removed: list[str] = []
    kept: list[str] = []
    for line in original_text.splitlines():
        if line.strip() and line.strip() in furniture:
            removed.append(line.strip())
            continue
        kept.append(line)
    if not removed:
        return original_text, []
    return "\n".join(kept).strip(), removed


# --------------------------------------------------------------------------- #
# product result state
# --------------------------------------------------------------------------- #


def is_plausible(score: float | None, best: float | None) -> bool:
    """Higher cosine similarity is better; a passage inside the band is shown."""
    if score is None or best is None:
        return True
    if best == 0:
        return score == best
    return (best - score) <= abs(best) * PLAUSIBLE_BAND


def classify_result_state(objects: list[dict], *, searchable: bool) -> dict:
    """Map candidate evidence onto the four required product result states."""
    if not searchable:
        return {
            "state": STATE_INSUFFICIENT_SOURCE,
            "label_zh": "当前来源无法提供足够的可检索一手文本",
            "explanation_zh": (
                "该来源没有可用文本层，也没有可用的 OCR 缓存，因此当前资料源不足以核验；"
                "这表示“本产品现在无法核验”，不表示该文献或该说法不存在。"
            ),
        }

    located = [
        item
        for item in objects
        if item["status"] == "located" and item.get("highlighted_image_refs")
    ]
    if not located:
        return {
            "state": STATE_NO_CORRESPONDING_PASSAGE,
            "label_zh": "当前来源可检索，但没有找到可靠的对应段落",
            "explanation_zh": (
                "来源文本可以检索，但排序结果里没有能定位到原文页面的段落；"
                "产品不会为了给出答案而制造匹配。"
            ),
        }

    scores = [
        item["retrieval_score"]
        for item in located
        if item["retrieval_score"] is not None
    ]
    best = max(scores) if scores else None
    plausible = [item for item in located if is_plausible(item["retrieval_score"], best)]
    if len(plausible) >= 2:
        return {
            "state": STATE_MULTIPLE_CANDIDATES,
            "label_zh": f"找到 {len(plausible)} 个可能对应的段落，未强制选出唯一答案",
            "explanation_zh": (
                "多个段落的检索相关性接近，产品并列展示，由使用者判断；"
                "排序分数只是检索判断，不是来源证据。"
            ),
        }
    return {
        "state": STATE_EVIDENCE_FOUND,
        "label_zh": "找到可靠的对应段落（已定位到原页并可高亮）",
        "explanation_zh": (
            "该段落已定位到具体 PDF 页面并生成了高亮原页图像；"
            "印刷页码若未确认则保持未解析。"
        ),
    }


# --------------------------------------------------------------------------- #
# the canonical run
# --------------------------------------------------------------------------- #


def _resolve_searchability(
    resolved: dict,
    *,
    ocr_mode: str,
    log=print,
) -> dict:
    """Decide which search route this source supports right now."""
    text_report = scan_source_text_layer(resolved["pdf"])
    ocr_report = ocr_cache_report(resolved["ocr_cache"])
    decision = {
        "text_layer": text_report,
        "ocr_cache": ocr_report,
        "route": None,
        "blockers": [],
    }

    if text_report["status"] == "searchable":
        decision["route"] = "text_layer"
        return decision

    if resolved["ocr_cache"] is not None and ocr_report["present"]:
        decision["route"] = "ocr"
        return decision

    if ocr_mode == "force":
        if resolved["ocr_cache"] is None:
            decision["blockers"].append("no_ocr_cache_path_configured")
        else:
            log(
                f"OCR requested for {resolved['source_id']}: "
                "this reads every page with RapidOCR and is slow"
            )
            oe.ocr_document(resolved["pdf"], cache_dir=resolved["ocr_cache"])
            decision["ocr_cache"] = ocr_cache_report(resolved["ocr_cache"])
            if decision["ocr_cache"]["present"]:
                decision["route"] = "ocr"
                return decision
            decision["blockers"].append("ocr_produced_no_text")

    decision["blockers"].append("no_text_layer_and_no_ocr_cache")
    return decision


def run_pipeline(
    *,
    secondary_text: str,
    hints: str = "",
    source: dict,
    out_dir: Path,
    settings_path: Path = DEFAULT_SETTINGS,
    retrieval_mode: str = "local",
    ocr_mode: str = "auto",
    k: int = 10,
    dpi: float = ev.DEFAULT_DPI,
    radius: int = 1,
    cache_dir: Path | None = DEFAULT_CACHE_DIR,
    log=print,
) -> dict:
    """Run the canonical product pipeline for one secondary input + source."""
    _offline_model_env()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir = out_dir / "images"
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    secondary_text = (secondary_text or "").strip()
    hints = (hints or "").strip()
    if not secondary_text:
        raise SystemExit("secondary_text is required")

    resolved = source if isinstance(source.get("metadata"), dict) else resolve_paths(source)
    settings = load_settings(settings_path)
    chunk_chars, chunk_overlap = chunk_params(settings)

    run: dict = {
        "result_version": RESULT_VERSION,
        "started_at": started_at,
        "entrypoint": "tools/mvp_app.py",
        "retrieval_mode": retrieval_mode,
        "ocr_mode": ocr_mode,
        "secondary_chars": len(secondary_text),
        "hint_chars": len(hints),
        "hints_provided": bool(hints),
        "chunk_chars": chunk_chars,
        "chunk_overlap": chunk_overlap,
        "embedding": str(settings.embedding),
        "k": k,
        "model_calls": 0,
        "cost_usd": 0.0,
    }
    source_info: dict = {
        "source_id": resolved["source_id"],
        "label": resolved["label"],
        "pdf": repo_relative(resolved["pdf"]),
        "pdf_sha256": sha256_of(resolved["pdf"]),
        "metadata": resolved["metadata"],
        "notes": resolved.get("notes"),
    }

    decision = _resolve_searchability(resolved, ocr_mode=ocr_mode, log=log)
    route = decision["route"]
    source_info["route"] = route or "unavailable"
    source_info["blockers"] = decision["blockers"]
    source_info["text_layer_pages_with_usable_text"] = decision["text_layer"][
        "pages_with_usable_text_layer"
    ]
    source_info["page_count"] = decision["text_layer"]["page_count"]
    source_info["ocr_cache_pages"] = decision["ocr_cache"]["pages"]

    if route is None:
        run["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        return {
            "result_version": RESULT_VERSION,
            "run": run,
            "source": source_info,
            "searchability": decision,
            "result_state": classify_result_state([], searchable=False),
            "candidates": [],
            "counts": {"candidates": 0, "located": 0, "highlight_images": 0},
        }

    index_started = time.perf_counter()
    metadata = resolved["metadata"]
    citation = (
        resolved.get("citation")
        or t004.build_citations(metadata)["basic_reference_citation"]
        or resolved["docname"]
    )
    page_texts: dict[str, str] = {}
    ocr_pages: dict[int, dict] = {}
    if route == "text_layer":
        page_texts, parse_info = parse_pdf_pages(resolved["pdf"], cache_dir=cache_dir)
        doc, chunks = chunk_pages(
            page_texts,
            docname=resolved["docname"],
            citation=citation,
            chunk_chars=chunk_chars,
            overlap=chunk_overlap,
        )
    else:
        ocr_pages = oe.load_cached_pages(resolved["ocr_cache"])
        page_texts = {
            str(page): record["joined_text"]
            for page, record in ocr_pages.items()
            if record.get("joined_text")
        }
        parse_info = {
            "source": "ocr-cache",
            "seconds": 0.0,
            "page_count": len(page_texts),
        }
        doc, chunks = chunk_pages(
            page_texts,
            docname=resolved["docname"],
            citation=citation,
            chunk_chars=chunk_chars,
            overlap=chunk_overlap,
        )

    cache_key = source_cache_key(
        source_info["pdf_sha256"],
        route,
        chunk_chars,
        chunk_overlap,
        settings,
        resolved["docname"],
    )
    docs, embedding, indexed, cache_hit = build_or_get_index(
        chunks, doc, settings, cache_key
    )
    run["index_seconds"] = round(time.perf_counter() - index_started, 1)
    run["chunk_count"] = len(chunks)
    run["indexed"] = indexed
    run["index_cache_hit"] = cache_hit
    run["index_source"] = parse_info

    retrieval_started = time.perf_counter()
    primary = asyncio.run(rank_candidates(docs, embedding, secondary_text, k, settings))
    extra: list[dict] = []
    if hints:
        hint_query = f"{secondary_text}\n{hints}"
        extra = asyncio.run(rank_candidates(docs, embedding, hint_query, k, settings))
    candidates = asyncio.run(
        merge_candidates(primary, extra, embedding, secondary_text)
    )
    run["retrieval_seconds"] = round(time.perf_counter() - retrieval_started, 1)
    run["candidate_count"] = len(candidates)
    run["retrieval"] = "paperqa.docs.Docs.retrieve_texts (local embedding, no LLM)"

    if retrieval_mode == "llm":
        # Opt-in only: the accepted T004 PaperQA2 LLM reranking path. It needs a
        # provider key and spends money, so the product never selects it silently.
        raise SystemExit(
            "retrieval_mode=llm is not wired into the canonical product entry "
            "point yet; run tools/t004_backend_slice.py for that path"
        )

    evidence_started = time.perf_counter()
    if route == "text_layer":
        source_reader = ev.PdfEvidenceSource(resolved["pdf"], dpi=dpi)
        evidence_origin = "text_layer"
    else:
        source_reader = oe.OcrEvidenceSource(resolved["pdf"], ocr_pages, dpi=dpi)
        evidence_origin = "ocr"
    try:
        objects = build_evidence_objects(
            candidates,
            source_reader,
            metadata=metadata,
            images_dir=images_dir,
            dpi=dpi,
            radius=radius,
            evidence_origin=evidence_origin,
        )
    finally:
        source_reader.close()
    run["evidence_seconds"] = round(time.perf_counter() - evidence_started, 1)

    furniture = repeated_page_furniture(page_texts) if page_texts else set()
    for record in objects:
        display_text, removed = display_text_for(record.get("original_text") or "", furniture)
        record["display_text"] = display_text
        record["display_text_removed_lines"] = removed

    located = [
        item
        for item in objects
        if item["status"] == "located" and item.get("highlighted_image_refs")
    ]
    result_state = classify_result_state(objects, searchable=True)
    run["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    result = {
        "result_version": RESULT_VERSION,
        "run": run,
        "source": source_info,
        "searchability": decision,
        "secondary_text": secondary_text,
        "hints": hints,
        "result_state": result_state,
        "display_furniture_lines": sorted(furniture)[:50],
        "candidates": objects,
        "counts": {
            "candidates": len(objects),
            "located": len(located),
            "highlight_images": sum(len(item["highlighted_image_refs"]) for item in located),
        },
    }
    (out_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secondary-text", required=True)
    parser.add_argument("--hints", default="")
    parser.add_argument("--source", default=None, help="registry id/label or a PDF path")
    parser.add_argument("--source-label", default=None)
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--ocr-cache", type=Path, default=None)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument("--retrieval-mode", choices=("local", "llm"), default="local")
    parser.add_argument("--ocr-mode", choices=("auto", "off", "force"), default="auto")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--dpi", type=float, default=ev.DEFAULT_DPI)
    args = parser.parse_args(argv)

    if args.source is None:
        raise SystemExit("--source is required (registry id or a PDF path)")

    registry = load_sources(args.sources)
    known_ids = {str(entry.get("source_id")) for entry in registry}
    if args.source in known_ids:
        source = dict(find_source(registry, args.source))
        if args.ocr_cache is not None:
            source["ocr_cache"] = str(args.ocr_cache)
        if args.metadata is not None:
            source["metadata"] = str(args.metadata)
    else:
        pdf = Path(args.source)
        if not pdf.is_absolute():
            pdf = REPO_ROOT / pdf
        if not pdf.exists():
            available = ", ".join(sorted(known_ids))
            raise SystemExit(
                f"--source {args.source!r} is neither a registered source "
                f"({available}) nor an existing PDF path"
            )
        source = {
            "source_id": args.source_label or pdf.stem,
            "label": args.source_label or pdf.name,
            "pdf": str(pdf),
            "metadata": str(args.metadata) if args.metadata else "",
            "ocr_cache": str(args.ocr_cache) if args.ocr_cache else None,
            "docname": pdf.stem,
        }

    out_dir = args.out_dir or (DEFAULT_RUNS_DIR / time.strftime("cli-%Y%m%d-%H%M%S"))
    result = run_pipeline(
        secondary_text=args.secondary_text,
        hints=args.hints,
        source=source,
        out_dir=out_dir,
        settings_path=args.settings,
        retrieval_mode=args.retrieval_mode,
        ocr_mode=args.ocr_mode,
        k=args.k,
        dpi=args.dpi,
    )
    public = {
        "result_state": result["result_state"]["state"],
        "result_state_label_zh": result["result_state"]["label_zh"],
        "source": result["source"]["source_id"],
        "route": result["source"]["route"],
        "counts": result["counts"],
        "run": result["run"],
        "result_path": repo_relative(out_dir / "result.json"),
    }
    print(json.dumps(public, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

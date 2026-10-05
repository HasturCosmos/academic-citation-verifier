#!/usr/bin/env python
"""Product entry point for 二流文科生的二手文献引用助手.

One canonical product surface, two supported source routes:

    secondary-source text / PDF / photo  (+ optional fallible hints)
        + an uploaded / registered / local-path primary-source PDF
        -> searchable-text route (text layer, or the adopted RapidOCR fallback)
        -> ranked candidate passages with original-page highlight, PDF page,
           known bibliographic metadata and copyable Chinese citations

Two ways to use it:

* local web app (default)   -  ``python tools/mvp_app.py``
* headless single run       -  ``python tools/mvp_app.py --run-once ...``

The web surface binds to 127.0.0.1 only and has no accounts, no session storage
and no upload to any external service. Uploads, extracted text, page images and
run results are written below ``data/private/`` and are never committed.

The MVP milestone was accepted on 2026-10-02 (D019). This file carries the
post-MVP pilot patch that makes primary-source PDF upload the normal path and
turns blank/unsupported primary-source input into a friendly, explicit message.

Primary-source format policy (post-MVP patch): the evidence contract requires a
stable page geometry plus an original-page image, so the searchable source must
be a PDF. Blank metadata means "no metadata"; a metadata path is only read when
it really is a regular file.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import secrets
import sys
import threading
import time
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import mvp_pipeline as mvp  # noqa: E402
import source_acquisition as sa  # noqa: E402
import t006_ocr_benchmark as bench  # noqa: E402
import footnote_parse as fp  # noqa: E402

NL = chr(10)
CRLF = bytes((13, 10))
CRLFCRLF = CRLF + CRLF

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_UPLOAD_BYTES = 400 * 1024 * 1024
SECONDARY_OCR_MAX_PAGES = 5
MIN_SECONDARY_TEXT_CHARS = 60
# The lawful source finder returns a short list on purpose: it is a lead
# generator, not a search engine.
FINDER_RESULT_LIMIT = 6
FINDER_TOKEN_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

STATE_STYLE = {
    mvp.STATE_EVIDENCE_FOUND: ("evidence", "可靠证据已找到"),
    mvp.STATE_MULTIPLE_CANDIDATES: ("multiple", "有多个可能对应的段落"),
    mvp.STATE_NO_CORRESPONDING_PASSAGE: ("none", "未找到可靠的对应段落"),
    mvp.STATE_INSUFFICIENT_SOURCE: ("insufficient", "当前资料源不足以核验"),
}

STATUS_STYLE = {
    "located": "located",
    "ambiguous": "ambiguous",
    "unmatched": "unmatched",
    "needs_ocr": "needs-ocr",
}


# --------------------------------------------------------------------------- #
# secondary-source input handling
# --------------------------------------------------------------------------- #


def _normalized_len(text: str) -> int:
    return sum(1 for char in text if not char.isspace())


def _ocr_image(image_path: Path, engine=None) -> str:
    if engine is None:
        engine = bench.load_engine("rapidocr", None)
    return bench.recognize(engine, Path(image_path))["joined_text"]


def _pdf_text_layer(pdf_path: Path) -> tuple[str, int]:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(pdf_path))
    pages: list[str] = []
    try:
        for index in range(len(document)):
            page = document[index]
            try:
                textpage = page.get_textpage()
                try:
                    pages.append(textpage.get_text_range())
                finally:
                    textpage.close()
            finally:
                page.close()
    finally:
        document.close()
    return NL.join(pages), len(pages)


def _pdf_pages_to_images(
    pdf_path: Path, out_dir: Path, limit: int, dpi: float = 300.0
) -> list[Path]:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(pdf_path))
    rendered: list[Path] = []
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        for index in range(min(limit, len(document))):
            page = document[index]
            try:
                image = page.render(scale=dpi / 72.0).to_pil()
            finally:
                page.close()
            target = out_dir / f"page_{index + 1:04d}.png"
            image.save(target)
            rendered.append(target)
    finally:
        document.close()
    return rendered


def extract_secondary_text(
    *,
    pasted: str = "",
    upload_path: Path | None = None,
    work_dir: Path,
    allow_ocr: bool = True,
) -> dict:
    """Readable text from a pasted string, an uploaded PDF or an uploaded image.

    The extraction is deliberately simple and honest: a PDF text layer is used
    when it exists; otherwise (and for images) the adopted RapidOCR engine reads
    the page and the result is labelled as OCR. Nothing is inferred from a file
    name or from the user's hints.
    """
    info: dict = {
        "origin": "pasted",
        "file": None,
        "notes": [],
        "ocr_pages": 0,
        "text": "",
        "text_chars": 0,
    }
    if upload_path is None:
        info["text"] = pasted.strip()
        info["text_chars"] = len(info["text"])
        if info["text"]:
            info["notes"].append("文本来自粘贴输入，未经过 OCR。")
        return info

    upload_path = Path(upload_path)
    info["file"] = upload_path.name
    suffix = upload_path.suffix.lower()

    if suffix == ".pdf":
        text, page_count = _pdf_text_layer(upload_path)
        if _normalized_len(text) >= MIN_SECONDARY_TEXT_CHARS:
            info["origin"] = "secondary_pdf_text_layer"
            info["text"] = text.strip()
            info["notes"].append(
                f"从上传 PDF 的文本层读取（{page_count} 页，"
                f"{_normalized_len(text)} 个非空白字符）。"
            )
        elif allow_ocr:
            images = _pdf_pages_to_images(
                upload_path, work_dir / "secondary_pages", SECONDARY_OCR_MAX_PAGES
            )
            engine = bench.load_engine("rapidocr", None)
            info["origin"] = "secondary_pdf_ocr"
            info["ocr_pages"] = len(images)
            info["text"] = NL.join(_ocr_image(path, engine) for path in images).strip()
            info["notes"].append(
                f"上传的 PDF 没有可用文本层，已用 RapidOCR 识别前 {len(images)} 页；"
                "这是机器识别结果，请核对后再使用。"
            )
        else:
            info["origin"] = "secondary_pdf_unreadable"
            info["notes"].append("上传的 PDF 没有可用文本层，且本次未启用 OCR。")
    elif suffix in IMAGE_SUFFIXES:
        if allow_ocr:
            engine = bench.load_engine("rapidocr", None)
            info["origin"] = "secondary_image_ocr"
            info["ocr_pages"] = 1
            info["text"] = _ocr_image(upload_path, engine).strip()
            info["notes"].append("图片已用 RapidOCR 识别；这是机器识别结果，请核对后再使用。")
        else:
            info["origin"] = "secondary_image_ocr_disabled"
            info["notes"].append("本次未启用 OCR，无法读取图片内容。")
    elif suffix in (".txt", ".md"):
        info["origin"] = "secondary_text_file"
        info["text"] = upload_path.read_text(encoding="utf-8", errors="replace").strip()
        info["notes"].append("从纯文本文件读取。")
    else:
        info["origin"] = "unsupported_upload"
        info["notes"].append(f"暂不支持的文件类型：{suffix or '（无扩展名）'}")

    info["text_chars"] = len(info["text"])
    return info


def _paragraphs(text: str) -> list[str]:
    groups: list[str] = []
    current: list[str] = []
    for raw in text.splitlines():
        if raw.strip():
            current.append(raw.strip())
        elif current:
            groups.append(NL.join(current))
            current = []
    if current:
        groups.append(NL.join(current))
    return groups


def split_secondary_items(text: str, *, max_items: int = 12, min_chars: int = 12) -> list[str]:
    """A deliberately simple splitter for a page holding several quotations.

    Rule: blank lines first, then sentence-final punctuation for long blocks. It
    is a recall aid, not a parser: the confirm step lets the user edit the text
    by hand and choose which items to search, and the residual gap (no robust
    automatic multi-item detection without a new subsystem) is recorded in the
    MVP candidate report.
    """
    items: list[str] = []
    for block in _paragraphs(text):
        if len(block) <= min_chars * 3:
            items.append(block)
            continue
        for sentence in re.split(r"(?<=[。！？!?])", block):
            sentence = sentence.strip()
            if len(sentence) >= min_chars:
                items.append(sentence)
    if len(items) <= 1:
        return [text.strip()] if text.strip() else []
    return items[:max_items]


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #


CSS = """
:root{--ink:#18202a;--muted:#667085;--line:#d9e0e8;--bg:#f5f7f9;--card:#fff;
--ok:#176b42;--ok-soft:#edf7f1;--warn:#9a5b00;--warn-soft:#fff7e8;
--bad:#a63b32;--info:#315f8f;--info-soft:#eef5fb;--soft:#f8fafc;}
*{box-sizing:border-box}
body{font-family:system-ui,"Microsoft YaHei","PingFang SC",sans-serif;color:var(--ink);
background:var(--bg);margin:0;line-height:1.7}
main{max-width:1160px;margin:0 auto;padding:34px 22px 72px}
h1{font-size:26px;letter-spacing:-.02em;margin:0 0 5px}
h2{font-size:19px;margin:30px 0 12px;border-bottom:1px solid var(--line);padding-bottom:8px}
h3{font-size:15px;margin:16px 0 6px}
.sub{color:var(--muted);font-size:13px;margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin:14px 0}
.banner{border-radius:12px;padding:15px 17px;margin:16px 0;border-left:5px solid}
.banner b{display:block;font-size:15px;margin-bottom:3px}
.b-evidence{background:var(--ok-soft);border-color:var(--ok)}
.b-multiple{background:var(--info-soft);border-color:var(--info)}
.b-none{background:var(--warn-soft);border-color:var(--warn)}
.b-insufficient{background:#f0f2f5;border-color:#6b7280}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;color:#fff;vertical-align:middle}
.located{background:var(--ok)}.ambiguous{background:var(--warn)}
.unmatched{background:var(--bad)}.needs-ocr{background:#4b5563}
.tag{display:inline-block;padding:2px 8px;border:1px solid var(--line);border-radius:999px;font-size:12px;color:var(--muted);background:#fff;margin-right:6px}
.warn{background:var(--warn-soft);border-left:4px solid #e4a11b;padding:9px 11px;margin:9px 0;font-size:13px}
.ocr{background:var(--info-soft);border-left:4px solid var(--info);padding:9px 11px;margin:9px 0;font-size:13px}
table{border-collapse:collapse;width:100%;font-size:13px;margin:7px 0}
td,th{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
th{background:#fafbfc;width:190px;font-weight:600}
pre{white-space:pre-wrap;background:#f6f8fa;border:1px solid var(--line);border-radius:9px;padding:11px;font-family:inherit;font-size:14px;margin:9px 0}
textarea,input[type=text],input[type=number],input[type=file],select{width:100%;padding:9px;border:1px solid var(--line);border-radius:9px;font-family:inherit;font-size:14px;background:#fff}
textarea{min-height:120px}
label{display:block;font-weight:600;font-size:13px;margin:14px 0 4px}
button{background:#243447;color:#fff;border:0;border-radius:9px;padding:9px 16px;font-size:14px;cursor:pointer;margin-top:12px}
button.ghost{background:#fff;color:#243447;border:1px solid var(--line);padding:5px 10px;font-size:12px;margin:0}
button.ghost.right{float:right}
img{max-width:100%;border:1px solid var(--line);border-radius:9px;margin-top:8px}
details{border:1px solid var(--line);border-radius:12px;background:var(--card);margin:11px 0}
details>summary{cursor:pointer;padding:13px 15px;font-size:14px;font-weight:600;list-style:none}
details>summary::-webkit-details-marker{display:none}
details>div{padding:0 15px 15px}
details.dev{background:#fbfcfd;border-style:dashed}
details.dev>summary{color:var(--muted);font-size:13px;font-weight:500}
.muted{color:var(--muted);font-size:13px}
.log{font-family:ui-monospace,Consolas,monospace;font-size:12px;background:#0f1720;color:#d7e2ee;padding:12px;border-radius:8px;max-height:320px;overflow:auto;white-space:pre-wrap}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.hint{font-weight:400;display:block;margin:4px 0}
.result-header{margin-bottom:18px}
.result-header .source-line{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.evidence-hero{background:var(--card);border:1px solid #c9ded1;border-radius:18px;padding:24px;margin:18px 0;box-shadow:0 8px 28px rgba(24,32,42,.06)}
.evidence-kicker{display:inline-block;color:var(--ok);background:var(--ok-soft);font-size:12px;font-weight:700;padding:4px 9px;border-radius:999px;margin-bottom:8px}
.evidence-hero h2{font-size:22px;border:0;padding:0;margin:0 0 8px}
.evidence-hero-head{display:flex;justify-content:space-between;gap:24px;align-items:flex-start}
.page-stack{min-width:220px;text-align:right}
.page-primary{font-size:21px;font-weight:750;color:var(--ink);line-height:1.35}
.page-secondary{font-size:12px;color:var(--muted);margin-top:4px}
.evidence-section{margin-top:22px}
.evidence-section-title{font-size:13px;font-weight:750;color:#344054;margin-bottom:7px}
.evidence-text{font-size:16px;line-height:1.9;background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:17px 18px;white-space:pre-wrap}
.evidence-gallery{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:9px}
.evidence-gallery img{width:100%;margin:0;background:#fff}
.edition-card{background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:14px}
.meta-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 18px}
.meta-item{font-size:13px}.meta-item b{color:#475467;margin-right:6px}
.conflict-box{background:var(--warn-soft);border:1px solid #efd49c;border-radius:12px;padding:14px;margin-top:12px}
.conflict-box strong{display:block;color:#7a4700;margin-bottom:5px}
.conflict-row{font-size:13px;margin:5px 0}
.citation-box{border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-top:9px;background:#fff}
.citation-box pre{margin:7px 0 0;background:var(--soft)}
.alternatives{margin-top:20px}
.alternatives>summary{background:#fff}
.candidate-card>summary{display:flex;gap:10px;align-items:center;justify-content:space-between}
.candidate-summary-left{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.state-label{display:inline-block;padding:3px 9px;border-radius:999px;font-size:12px;font-weight:650;color:#fff}
.candidate-page{font-size:12px;color:var(--muted);font-weight:500}
.candidate-excerpt{font-size:14px;line-height:1.8;background:var(--soft);border-radius:10px;padding:12px;white-space:pre-wrap;margin:8px 0}
.unverified-page{font-size:12px;color:var(--warn);font-weight:650;margin:7px 0}
.decision-panel{background:var(--info-soft);border:1px solid #cbddee;border-radius:16px;padding:18px;margin:18px 0}
.decision-panel h2{border:0;margin:0 0 6px;padding:0}
.empty-state{background:#fff;border:1px solid var(--line);border-radius:16px;padding:20px;margin:18px 0}
.tech-inline{font-family:ui-monospace,Consolas,monospace;font-size:12px}
.back-link{margin-top:22px}

.result-page-main{max-width:none;width:100%;padding:24px 24px 40px;overflow-x:hidden}
.result-header{width:100%;margin:0 0 10px;text-align:center}
.brand-title{font-size:28px;line-height:1.3;font-weight:800;letter-spacing:.018em;margin:0}
.brand-title .brand-name{display:inline-block;border-bottom:3px solid #a9bfd3;padding:0 2px 1px}
.result-workspace{width:100%;max-width:1600px;margin:0 auto;
display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.08fr);gap:20px;align-items:start}
.result-left-zone{display:grid;grid-template-rows:auto auto auto;gap:14px;min-width:0}
.result-left-lower{display:grid;grid-template-columns:minmax(230px,.72fr) minmax(390px,1.28fr);
gap:20px;align-items:start;min-width:0}
.result-detail{position:sticky;top:18px;margin-top:50px;height:calc(100vh - 92px);
min-height:540px;max-height:980px;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;
scrollbar-gutter:stable;padding-right:6px}
.panel{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px}
.panel h2,.panel h3{border:0;margin:0 0 10px;padding:0}
.panel-title{font-size:13px;font-weight:750;color:#344054;margin-bottom:7px}
.source-drop{position:relative;border:1.5px dashed #aeb9c7;border-radius:14px;background:#fff;
min-height:88px;display:flex;align-items:center;gap:14px;padding:14px 16px;overflow:hidden;transition:.15s ease}
.source-drop:hover,.source-drop.drag{border-color:#315f8f;background:#f8fbff}
.source-drop input[type=file]{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer}
.pdf-icon{width:44px;height:54px;border:2px solid #d24b43;border-radius:7px;display:flex;align-items:center;
justify-content:center;color:#b42318;font-weight:800;font-size:14px;background:#fff6f5;flex:0 0 auto}
.source-copy b{display:block;font-size:15px;margin:0;max-width:520px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.source-action{font-size:12px;color:#315f8f;font-weight:700;margin-top:5px}
.source-route{display:inline-block;font-size:11px;color:#667085;background:#f2f4f7;border-radius:999px;padding:2px 7px;margin-left:7px}
.meta-card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px}
.meta-card .meta-grid{grid-template-columns:1fr;gap:7px}
.conflict-card{background:var(--warn-soft);border:1px solid #efd49c;border-radius:14px;padding:13px 14px;margin-top:12px}
.conflict-card-title{display:block;color:#8a4d00;font-size:13px;font-weight:800;margin-bottom:6px}
.compact-conflict-line{font-size:12px;color:#667085;line-height:1.65}
.status-merge{background:var(--info-soft);border:1px solid #cbddee;border-radius:16px;padding:16px 17px;margin-bottom:12px}
.status-merge b{display:block;font-size:16px;margin-bottom:4px}.status-merge p{margin:0;color:#52637a;font-size:13px}
.candidate-list{display:flex;flex-direction:column;gap:9px}
.candidate-choice{display:flex;align-items:center;justify-content:space-between;gap:14px;background:#fff;
border:1px solid var(--line);border-radius:12px;padding:12px 14px;min-height:62px;transition:.15s ease}
.candidate-choice.selected{border-color:#3777ad;background:#f4f9fd;box-shadow:0 0 0 2px rgba(49,95,143,.08)}
.candidate-choice-main{display:flex;align-items:center;gap:10px;min-width:0;flex:1}
.candidate-choice .state-label{white-space:nowrap;flex:0 0 auto}
.candidate-choice .candidate-page{font-size:13px;color:#344054;font-weight:700;white-space:nowrap;flex:0 0 auto}
.candidate-choice button{margin:0;padding:7px 11px;font-size:12px;background:#fff;color:#315f8f;
border:1px solid #bfd1e2;white-space:nowrap;flex:0 0 auto}
.current-mark{display:none;font-size:11px;font-weight:750;color:#315f8f;background:#e8f2fa;
border-radius:999px;padding:2px 7px;white-space:nowrap;flex:0 0 auto}
.candidate-choice.selected .current-mark{display:inline-block}
.other-candidates{margin-top:12px}.other-candidates>summary{padding:11px 12px}
.detail-panel{display:none;background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px}
.detail-panel.active{display:block}
.detail-block{margin-top:0}.detail-block + .detail-block{margin-top:18px}
.detail-gallery{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.detail-gallery img{width:100%;margin:0;background:#fff}
.detail-text{background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:15px;white-space:pre-wrap;line-height:1.85}
.detail-empty{background:var(--soft);border:1px dashed var(--line);border-radius:12px;padding:18px;color:#667085}
.citations-inline{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.citations-inline .citation-box{margin:0}
.result-back{margin-top:14px}
@media(max-width:1280px){
  .result-left-lower{grid-template-columns:minmax(210px,.68fr) minmax(360px,1.32fr)}
  .candidate-choice{gap:10px;padding-left:11px;padding-right:11px}
}
@media(max-width:760px){
  .grid,.meta-grid,.evidence-gallery{grid-template-columns:1fr}
  .evidence-hero-head{display:block}.page-stack{text-align:left;margin-top:12px;min-width:0}
  main{padding:24px 14px 56px}.evidence-hero{padding:18px}
}
"""

CANDIDATE_STATUS_ZH = {
    "located": "已定位到原页，可回查",
    "unmatched": "检索到相近文本，但未能稳定定位原页",
    "ambiguous": "找到文本，但原页位置不唯一，需要人工核对",
    "needs_ocr": "当前页面缺少可稳定定位的文本，需要 OCR / 人工核对",
}

BIB_FIELD_LABEL_ZH = {
    "author": "作者",
    "author_country": "作者国别",
    "title": "书名 / 篇名",
    "translator": "译者",
    "publisher_place": "出版地",
    "publisher": "出版社",
    "year": "年份",
    "isbn": "ISBN",
    "document_type": "文献类型",
    "printed_page": "印刷页码",
}


def _human_candidate_status(status: str) -> str:
    return CANDIDATE_STATUS_ZH.get(status, "当前证据状态需要人工核对")


def _status_class(status: str) -> str:
    return STATUS_STYLE.get(status, "unmatched")


def _format_page_values(values: object) -> str:
    if values in (None, "", []):
        return "—"
    if isinstance(values, (list, tuple)):
        cleaned = [str(item) for item in values if item not in (None, "")]
        if not cleaned:
            return "—"
        if len(cleaned) == 1:
            return cleaned[0]
        try:
            ints = [int(item) for item in cleaned]
        except (TypeError, ValueError):
            return "、".join(cleaned)
        if ints == list(range(ints[0], ints[0] + len(ints))):
            return f"{ints[0]}–{ints[-1]}"
        return "、".join(cleaned)
    return str(values)


def _verified_page_summary(candidate: dict) -> tuple[str, str]:
    printed = candidate.get("printed_page_numbers") or []
    pdf_pages = candidate.get("pdf_page_numbers") or []
    if printed:
        primary = "印刷页 " + _format_page_values(printed)
        secondary = "PDF 顺序页 " + _format_page_values(pdf_pages)
        return primary, secondary
    if pdf_pages:
        return (
            "PDF 顺序页 " + _format_page_values(pdf_pages),
            "印刷页码尚未确认，不会用 PDF 页号顶替",
        )
    return "页码尚未确认", "当前没有可核实的稳定原页位置"


def _plausible_located_candidates(result: dict) -> list[dict]:
    located = [
        item
        for item in result.get("candidates", [])
        if item.get("status") == "located" and item.get("highlighted_image_refs")
    ]
    scores = [item.get("retrieval_score") for item in located if item.get("retrieval_score") is not None]
    best = max(scores) if scores else None
    return [item for item in located if mvp.is_plausible(item.get("retrieval_score"), best)]


def _copy_button(target_id: str, label: str = "复制") -> str:
    return (
        f"<button class='ghost right' type='button' "
        f"onclick=\"navigator.clipboard.writeText("
        f"(document.getElementById('{target_id}').value "
        f"|| document.getElementById('{target_id}').textContent))\">"
        f"{html.escape(label)}</button>"
    )


def page(title: str, body: str, main_class: str = "") -> str:
    class_attr = f" class='{html.escape(main_class)}'" if main_class else ""
    return (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
        f"<body><main{class_attr}>{body}</main></body></html>"
    )


def _source_options(sources: list[dict], selected_id: str | None = None) -> str:
    options = []
    for source in sources:
        source_id = str(source.get("source_id"))
        label = html.escape("内置示例 · " + str(source.get("label") or source_id))
        selected = " selected" if selected_id == source_id else ""
        options.append(f"<option value='{html.escape(source_id)}'{selected}>{label}</option>")
    return "".join(options)


def _primary_source_summary(prefill: dict) -> str:
    """One-line description of the primary source the run will actually use."""
    upload = str(prefill.get("primary_upload") or "").strip()
    if upload:
        return "你上传的一手文献 PDF：" + html.escape(Path(upload).name)
    source_path = str(prefill.get("source_path") or "").strip()
    if source_path:
        return "本地 PDF 路径（高级选项）：" + html.escape(source_path)
    return "内置示例 / 已缓存资料源（使用下拉框所选条目）"


EVIDENCE_METADATA_FIELDS = (
    ("author", "作者"),
    ("author_country", "作者国别（如 德）"),
    ("title", "书名 / 篇名"),
    ("translator", "译者"),
    ("publisher_place", "出版地"),
    ("publisher", "出版社"),
    ("year", "年份"),
    ("isbn", "ISBN"),
    ("document_type", "文献类型（书籍填 M）"),
)


def _evidence_metadata_inputs(prefill: dict | None = None) -> str:
    """Normal-UX fields for the identity of the PDF that supplies evidence."""
    prefill = prefill or {}
    parts = [
        "<details><summary>这份 PDF 与脚注可能不是同一版本？填写 PDF 本身的版本信息</summary>",
        "<p class='muted'>这些字段描述你实际上传、并将作为原页证据的 PDF。"
        "如果它和上面的二手脚注冲突，系统会同时保留两套信息，但证据引用采用这份 PDF 的版本。"
        "不确定的字段可以留空。</p>",
        "<div class='grid'>",
    ]
    for key, label in EVIDENCE_METADATA_FIELDS:
        value = html.escape(str(prefill.get(f"evidence_{key}") or ""))
        parts.append(
            f"<div><label>{html.escape(label)}</label>"
            f"<input type='text' name='evidence_{key}' value='{value}'></div>"
        )
    parts.append("</div></details>")
    return "".join(parts)


def render_form(sources: list[dict], *, message: str = "", prefill: dict | None = None) -> str:
    prefill = prefill or {}
    footnote = prefill.get("footnote", prefill.get("hints", ""))
    body = [
        "<h1>二流文科生的二手文献引用助手</h1>",
        "<p class='sub'>读二手文献时看到可用的引用或转述，把它和对应的脚注/尾注一起交给它："
        "它先按脚注定向识别被引的一手作品和可能的中文出版物，找到或接收对应 PDF 后，"
        "在中文版原页里定位原文，给出可复制的原文、原页高亮、页码和中文引用。</p>",
        f"<div class='warn'>{html.escape(message)}</div>" if message else "",
        "<div class='card'><form id='main-form' method='post' action='/identify' "
        "enctype='multipart/form-data'>",
        _identity_hidden(prefill),
        "<label>① 二手文献内容（引用 / 转述，可直接粘贴）</label>",
        "<textarea name='secondary_text' placeholder='把二手文献中的引用、转述或整页文字粘贴到这里'>"
        + html.escape(str(prefill.get("secondary_text", "")))
        + "</textarea>",
        "<label>或上传二手文献页面（截图 / PDF / txt）</label>",
        "<input type='file' name='secondary_file' "
        "accept='.pdf,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,.txt,.md'>",
        "<label>② 对应脚注 / 尾注（系统据此定向查找一手文献）</label>",
        "<textarea name='footnote' placeholder='把这段引用对应的脚注或尾注粘贴到这里："
        "作者、篇名或书名、年份、页码、译者、出版社、卷期等，能填多少填多少；"
        "不确定也没关系，系统识别后你可以修改。'>"
        + html.escape(str(footnote))
        + "</textarea>",
        "<label>或上传脚注截图（自动 OCR）</label>",
        "<input type='file' name='footnote_file' "
        "accept='.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff'>",
        "<label>③ 一手文献</label>",
        "<p class='muted'>没有 PDF？先让系统根据上面的脚注定向识别被引作品和可能的中文出版物，"
        "再去找可合法访问的对应 PDF。</p>",
        "<button type='submit'>识别来源并开始核验 →</button>",
        "<p class='muted'>或者：我已经有对应的中文版 PDF，直接上传核验（不经过来源查找）。"
        "有文本层的 PDF 最快，扫描本会走 RapidOCR。文件只保存在本机 "
        "<code>data/private/</code> 下，不会上传。EPUB 没有固定页码和原页图像，"
        "不能作为核验来源。</p>",
        "<input type='file' name='primary_file' accept='.pdf'>",
        _evidence_metadata_inputs(prefill),
        "<button type='submit' formaction='/extract'>上传一手文献 PDF，直接核验 →</button>",
        "<details class='dev'><summary>开发者 / 高级选项（正常情况下不用打开）</summary><div>",
        "<label>内置示例 / 已缓存资料源（演示用）</label>",
        f"<select name='source'>{_source_options(sources, prefill.get('source'))}</select>",
        "<label>本地 PDF 路径（会覆盖上面的选择）</label>",
        "<input type='text' name='source_path' placeholder='例如 D:/books/某本书.pdf'>",
        "<label>元数据 JSON 路径（可选，用于生成引用；留空表示不提供）</label>",
        "<input type='text' name='metadata_path' placeholder='例如 D:/books/某本书.metadata.json'>",
        "<div class='grid'>",
        "<div><label>检索深度 k</label>"
        "<input type='number' name='k' value='10' min='1' max='50'></div>",
        "<div><label>扫描本 OCR 策略</label><select name='ocr_mode'>",
        "<option value='auto'>auto：有 OCR 缓存才用（推荐）</option>",
        "<option value='off'>off：完全不做 OCR</option>",
        "<option value='force'>force：现在 OCR 整本扫描（很慢）</option>",
        "</select></div></div>",
        "<label>补充线索（旧版自由文本，可选）</label>",
        "<textarea name='hints' placeholder='可选：脚注之外的记忆线索。'>"
        + html.escape(str(prefill.get("hints", "")))
        + "</textarea>",
        "</div></details>",
        "</form></div>",
        "<details class='dev'><summary>高级：直接查找开放全文（开发者 / 排障用）</summary><div>",
        "<form method='post' action='/find' "
        "onsubmit=\"var m=document.getElementById('main-form').elements;"
        "this.elements['secondary_text'].value=m['secondary_text'].value;"
        "this.elements['footnote'].value=m['footnote'].value;"
        "this.elements['hints'].value=m['hints'].value;\">"
        "<p class='muted'>正常流程不需要这一步。这里只用公开、免费、无需账号的开放获取接口"
        "（OpenAlex、Internet Archive、Google Books、中文维基文库），不会绕过付费墙、登录"
        "或借阅限制；只有点击下面的按钮时才会联网。</p>"
        + _hidden("secondary_text", "")
        + _hidden("footnote", "")
        + _hidden("hints", "")
        + _identity_hidden(prefill)
        + "<label>查找开放全文</label>"
        "<input type='text' name='find_query' placeholder='书名 / 作者 / ISBN / DOI'>"
        "<button type='submit'>查找开放全文 →</button>"
        "</form></div></details>",
        "<div class='card muted'><b>隐私与成本</b><br>所有文本、图片和结果都写在本地 "
        "<code>data/private/</code>，不上传到任何服务器；默认检索完全离线，"
        "不调用任何付费模型（0 次模型调用 / $0.00）。只有当你点击“识别来源”、"
        "“查找开放全文”或下载开放 PDF 时，才会访问公开的开放获取接口。</div>",
    ]
    return page("二手文献引用助手", "".join(body))


def render_confirm(info: dict, prefill: dict) -> str:
    items = split_secondary_items(info.get("text") or "")
    body = [
        "<h1>确认要检索的文本</h1>",
        "<p class='sub'>这一步是刻意的：文字识别和“整页里有几条引用”的自动判断都可能出错，"
        "所以检索之前由你确认或修改。</p>",
    ]
    for note in info.get("notes", []):
        body.append(f"<div class='warn'>{html.escape(note)}</div>")
    if "ocr" in str(info.get("origin", "")):
        body.append(
            "<div class='ocr'>当前输入来自图片识别（OCR），请与原始页面核对后再检索。</div>"
        )
    body.append(
        "<div class='card'><form method='post' action='/run' enctype='multipart/form-data'>"
    )
    if len(items) > 1:
        body.append(
            f"<p class='muted'>检测到 {len(items)} 个可能的条目（简单按空行和句末标点切分，可能不准）。"
            "勾选要检索的条目；如果不勾选，就使用下面编辑好的完整文本。</p>"
        )
        for index, item in enumerate(items):
            body.append(
                f"<label class='hint'><input type='checkbox' name='item' value='{index}' checked> "
                f"{html.escape(item[:140])}</label>"
            )
        body.append(
            "<input type='hidden' name='items_json' value='"
            + html.escape(json.dumps(items, ensure_ascii=False))
            + "'>"
        )
    body.append("<label>最终检索文本（可编辑）</label>")
    body.append(f"<textarea name='secondary_text'>{html.escape(info.get('text') or '')}</textarea>")
    body.append("<label>对应脚注 / 尾注（用作定向检索线索，可编辑）</label>")
    body.append(
        f"<textarea name='footnote'>{html.escape(str(prefill.get('footnote') or prefill.get('hints') or ''))}</textarea>"
    )
    body.append(_hidden("hints", prefill.get("hints") or ""))
    body.append("<label>一手文献来源</label>")
    body.append(f"<div class='card'><b>本次使用：</b>{_primary_source_summary(prefill)}</div>")
    body.append(
        "<p class='muted'>想换来源就返回上一步重新选择或上传。上传了 PDF 时以上传件为准，"
        "下面的下拉框（内置示例 / 已缓存资料源）只在没有上传时生效。</p>"
    )
    body.append("<details class='dev'><summary>开发者 / 高级选项</summary><div>")
    body.append(f"<select name='source'>{_source_options(prefill['_sources'], prefill.get('source'))}</select>")
    body.append(
        "<div class='grid'>"
        f"<div><label>检索深度 k</label><input type='number' name='k' "
        f"value='{html.escape(str(prefill.get('k', '10')))}'></div>"
        "<div><label>扫描本 OCR 策略</label><select name='ocr_mode'>"
        + "".join(
            f"<option value='{mode}'"
            + (" selected" if prefill.get("ocr_mode", "auto") == mode else "")
            + f">{mode}</option>"
            for mode in ("auto", "off", "force")
        )
        + "</select></div></div>"
    )
    body.append("</div></details>")
    body.append(
        "<input type='hidden' name='primary_upload' value='"
        + html.escape(str(prefill.get("primary_upload") or ""))
        + "'><input type='hidden' name='primary_metadata' value='"
        + html.escape(str(prefill.get("primary_metadata") or ""))
        + "'><input type='hidden' name='source_path' value='"
        + html.escape(str(prefill.get("source_path") or ""))
        + "'><input type='hidden' name='metadata_path' value='"
        + html.escape(str(prefill.get("metadata_path") or ""))
        + "'><input type='hidden' name='secondary_origin' value='"
        + html.escape(str(info.get("origin") or "pasted"))
        + "'><input type='hidden' name='secondary_file' value='"
        + html.escape(str(info.get("file") or ""))
        + "'>"
    )
    body.append(_identity_hidden(prefill))
    body.append("<button type='submit'>开始检索一手文献 →</button></form></div>")
    return page("确认检索文本", "".join(body))


def render_job(job_id: str, job: dict) -> str:
    status = job.get("status")
    body = [
        "<h1>正在检索一手文献</h1>",
        "<p class='sub'>检索在本地运行：文本扫描 → 分块 → 本地向量检索 → 原页定位与高亮。"
        "首次索引一本 1800 页的书大约需要几分钟，同一本书之后会走解析缓存。</p>",
    ]
    if status == "done":
        body.append(
            "<div class='banner b-evidence'><b>完成</b>"
            f"<a href='/result/{job_id}'>查看结果</a></div>"
        )
        body.append(f"<meta http-equiv='refresh' content='0;url=/result/{job_id}'>")
    elif status == "error":
        body.append("<div class='banner b-none'><b>运行失败</b>没有生成结果，错误见下方日志。</div>")
    else:
        body.append(
            "<div class='banner b-multiple'><b>运行中…</b>本页每 5 秒自动刷新。</div>"
            "<meta http-equiv='refresh' content='5'>"
        )
    body.append("<h2>运行日志</h2>")
    body.append("<div class='log'>" + html.escape(NL.join(job.get("log", []))) + "</div>")
    if job.get("error"):
        body.append("<h2>错误</h2><div class='log'>" + html.escape(job["error"]) + "</div>")
    body.append("<p><a href='/'>← 返回</a></p>")
    return page("运行中", "".join(body))


def _render_metadata_summary(metadata: dict) -> str:
    hidden = {"document_id", "metadata_origin", "metadata_provenance", "metadata_conflicts", "chinese_edition_confirmed"}
    items = [
        (BIB_FIELD_LABEL_ZH.get(key, str(key)), value)
        for key, value in metadata.items()
        if key not in hidden and value not in (None, "", [])
    ]
    if not items:
        return "<p class='muted'>这份证据 PDF 暂无足够的已确认书目信息。</p>"
    return (
        "<div class='meta-grid'>"
        + "".join(
            "<div class='meta-item'><b>"
            + html.escape(str(label))
            + "</b>"
            + html.escape(_format_page_values(value) if isinstance(value, list) else str(value))
            + "</div>"
            for label, value in items
        )
        + "</div>"
    )


def _render_conflicts(metadata: dict) -> str:
    conflicts = metadata.get("metadata_conflicts") or {}
    rows: list[str] = []
    for key, detail in conflicts.items():
        if not isinstance(detail, dict):
            continue
        label = BIB_FIELD_LABEL_ZH.get(str(key), str(key))
        rows.append(
            "<div class='conflict-row'><b>"
            + html.escape(label)
            + "</b>：二手脚注 / 确认线索为“"
            + html.escape(str(detail.get("confirmed") or "—"))
            + "”；证据 PDF 记录为“"
            + html.escape(str(detail.get("source_record") or "—"))
            + "”。本次证据引用采用“"
            + html.escape(str(detail.get("used") or "—"))
            + "”。</div>"
        )
    if not rows:
        return ""
    return (
        "<div class='conflict-box'><strong>版本信息有冲突，系统没有替你抹平</strong>"
        "<p class='muted'>二手脚注只作为导航线索；最终证据来自实际上传并定位到原页的 PDF。"
        "下面同时保留两套信息，便于你回查。</p>"
        + "".join(rows)
        + "</div>"
    )


def _render_citation_output(candidate: dict, run_id: str) -> str:
    metadata = candidate.get("bibliographic_metadata") or {}
    footnote = candidate.get("basic_footnote_citation")
    reference = candidate.get("basic_reference_citation")
    if not footnote:
        hint = ""
        if metadata.get("chinese_edition_confirmed") is False:
            hint = " 尚未确认对应中文出版物，因此不会把外文原作伪装成中文版引用。"
        return "<div class='citation-box'><b>引用暂未生成</b><p class='muted'>缺少已确认的书目信息。" + html.escape(hint) + "</p></div>"
    candidate_id = str(candidate.get("candidate_id") or "candidate")
    footnote_id = f"fn_{run_id}_{candidate_id}"
    reference_id = f"rf_{run_id}_{candidate_id}"
    return (
        "<div class='citation-box'><b>脚注</b>"
        + _copy_button(footnote_id, "复制脚注")
        + f"<pre id='{footnote_id}'>{html.escape(str(footnote))}</pre></div>"
        + "<div class='citation-box'><b>参考文献</b>"
        + _copy_button(reference_id, "复制参考文献")
        + f"<pre id='{reference_id}'>{html.escape(str(reference or ''))}</pre></div>"
    )


def _render_highlight_gallery(candidate: dict, run_id: str, *, compact: bool = False) -> str:
    refs = candidate.get("highlighted_image_refs") or []
    if candidate.get("status") != "located" or not refs:
        return ""
    return (
        "<div class='evidence-gallery'>"
        + "".join(
            "<img src='/asset?run="
            + html.escape(run_id)
            + "&ref="
            + urllib.parse.quote(str(ref))
            + "' alt='已核实的一手文献原页高亮'>"
            for ref in refs
        )
        + "</div>"
    )


def _render_candidate_debug(candidate: dict) -> str:
    rows = [
        ("candidate_id", candidate.get("candidate_id")),
        ("raw status", candidate.get("status")),
        ("检索位次", candidate.get("retrieval_rank")),
        ("相似度", candidate.get("retrieval_score")),
        ("检索页标签", candidate.get("retrieval_page_label")),
        ("PDF 顺序页", candidate.get("pdf_page_numbers") or "—"),
        ("印刷页码", candidate.get("printed_page_numbers") or "—"),
        ("证据来源", candidate.get("evidence_origin") or "—"),
    ]
    return (
        "<details class='dev'><summary>技术细节（开发者）</summary><div><table>"
        + "".join(
            f"<tr><th>{html.escape(str(key))}</th><td class='tech-inline'>{html.escape(str(value))}</td></tr>"
            for key, value in rows
        )
        + "</table></div></details>"
    )


def _render_primary_evidence(candidate: dict, run_id: str) -> str:
    metadata = candidate.get("bibliographic_metadata") or {}
    display = candidate.get("display_text") or candidate.get("original_text") or ""
    candidate_id = str(candidate.get("candidate_id") or "candidate")
    text_id = f"text_{run_id}_{candidate_id}"
    primary_page, secondary_page = _verified_page_summary(candidate)
    parts = [
        "<section class='evidence-hero'>",
        "<div class='evidence-kicker'>已定位到原页，可回查</div>",
        "<div class='evidence-hero-head'><div>",
        "<h2>找到的对应中文版原文</h2>",
        "<p class='muted'>下面这段文字已经重新定位到实际 PDF 原页；检索分数不作为证据本身。</p>",
        "</div><div class='page-stack'>",
        f"<div class='page-primary'>{html.escape(primary_page)}</div>",
        f"<div class='page-secondary'>{html.escape(secondary_page)}</div>",
        "</div></div>",
        "<div class='evidence-section'><div class='evidence-section-title'>一手原文</div>",
        _copy_button(text_id, "复制原文"),
        f"<div class='evidence-text' id='{text_id}'>{html.escape(display)}</div></div>",
        "<div class='evidence-section'><div class='evidence-section-title'>原页证据</div>",
        "<p class='muted'>高亮只在系统能够把候选文字稳定映射回 PDF 页面时生成。</p>",
        _render_highlight_gallery(candidate, run_id),
        "</div>",
        "<div class='evidence-section'><div class='evidence-section-title'>证据版本</div>",
        "<div class='edition-card'>",
        _render_metadata_summary(metadata),
        "</div>",
        _render_conflicts(metadata),
        "</div>",
        "<div class='evidence-section'><div class='evidence-section-title'>可复制引用</div>",
        _render_citation_output(candidate, run_id),
        "</div>",
        _render_candidate_debug(candidate),
        "</section>",
    ]
    return "".join(parts)


def _render_candidate(candidate: dict, run_id: str) -> str:
    status = str(candidate.get("status") or "")
    status_label = _human_candidate_status(status)
    status_class = _status_class(status)
    display = candidate.get("display_text") or candidate.get("original_text") or ""
    excerpt = display if len(display) <= 280 else display[:280].rstrip() + "……"
    if status == "located" and candidate.get("highlighted_image_refs"):
        primary_page, secondary_page = _verified_page_summary(candidate)
        page_label = primary_page
        page_note = f"<p class='muted'>{html.escape(secondary_page)}</p>"
    else:
        page_label = "尚未形成可核实的原页定位"
        hint = candidate.get("retrieval_page_label")
        page_note = (
            "<div class='unverified-page'>未核实页面线索："
            + html.escape(str(hint))
            + "（仅用于继续人工查找，不是已确认页码）</div>"
            if hint else ""
        )
    return (
        "<details class='candidate-card'><summary><span class='candidate-summary-left'>"
        f"<span class='state-label {status_class}'>{html.escape(status_label)}</span>"
        f"<span class='candidate-page'>{html.escape(page_label)}</span>"
        "</span><span class='muted'>展开查看</span></summary><div>"
        f"<div class='candidate-excerpt'>{html.escape(excerpt)}</div>"
        + page_note
        + _render_highlight_gallery(candidate, run_id, compact=True)
        + _render_candidate_debug(candidate)
        + "</div></details>"
    )


def _render_alternatives(title: str, candidates: list[dict], run_id: str) -> str:
    if not candidates:
        return ""
    return (
        "<details class='alternatives'><summary>"
        + html.escape(f"{title}（{len(candidates)}）")
        + "</summary><div>"
        + "".join(_render_candidate(candidate, run_id) for candidate in candidates)
        + "</div></details>"
    )


def _result_metadata(result: dict) -> dict:
    for candidate in result.get("candidates") or []:
        metadata = candidate.get("bibliographic_metadata") or {}
        if metadata:
            return metadata
    source = result.get("source") or {}
    metadata = source.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _render_compact_conflict(metadata: dict) -> str:
    conflicts = metadata.get("metadata_conflicts") or {}
    if not conflicts:
        return ""
    preferred = ["author", "translator", "publisher", "year"]
    rows = []
    for key in preferred:
        detail = conflicts.get(key)
        if not isinstance(detail, dict):
            continue
        label = BIB_FIELD_LABEL_ZH.get(key, key)
        rows.append(
            "<div class='compact-conflict-line'><b style='display:inline;color:#475467'>"
            + html.escape(label)
            + "</b>：脚注“"
            + html.escape(str(detail.get("confirmed") or "—"))
            + "” · PDF“"
            + html.escape(str(detail.get("source_record") or "—"))
            + "”</div>"
        )
    if not rows:
        return ""
    return (
        "<div class='conflict-card'><span class='conflict-card-title'>版本信息有冲突</span>"
        + "".join(rows)
        + "</div>"
    )


def _source_filename(source: dict) -> str:
    pdf = str(source.get("pdf") or "").strip()
    if pdf:
        return Path(pdf).name
    return str(source.get("label") or source.get("source_id") or "当前 PDF")


def _render_source_dropzone(result: dict, run_input: dict | None) -> str:
    source = result.get("source") or {}
    run_input = run_input or {}
    # Evidence-route labels remain explicit in code/probes even though normal UI only
    # surfaces an OCR badge when OCR materially affects evidence provenance.
    route_label = {
        "text_layer": "PDF 文本层（默认路径）",
        "ocr": "RapidOCR 扫描识别（可选路径）",
        "unavailable": "当前 PDF 暂不可检索",
    }.get(str(source.get("route") or ""), "")
    secondary_text = result.get("secondary_text") or run_input.get("secondary_text") or ""
    hints = result.get("hints") or run_input.get("hints") or ""
    confirmed_identity = run_input.get("confirmed_identity")
    filename = _source_filename(source)
    identity_hidden = (
        _hidden("identity_json", json.dumps(confirmed_identity, ensure_ascii=False))
        if confirmed_identity else ""
    )
    route_badge = (
        "<span class='source-route'>OCR 识别</span>"
        if source.get("route") == "ocr"
        else ""
    )
    return (
        "<section class='result-source'>"
        "<div class='panel-title'>来源</div>"
        "<form class='source-drop' id='source-swap-form' method='post' action='/rerun_source' "
        "enctype='multipart/form-data'>"
        "<div class='pdf-icon'>PDF</div>"
        "<div class='source-copy'><b>" + html.escape(filename) + route_badge + "</b>"
        "<div class='source-action'>拖入或点击更换 PDF；更换后自动重新核验</div></div>"
        "<input id='source-swap-input' type='file' name='primary_file' accept='application/pdf,.pdf' "
        "aria-label='更换一手文献 PDF'>"
        + _hidden("secondary_text", secondary_text)
        + _hidden("hints", hints)
        + _hidden("footnote", hints)
        + _hidden("k", str((run_input.get("options") or {}).get("k") or 12))
        + _hidden("ocr_mode", str((run_input.get("options") or {}).get("ocr_mode") or "auto"))
        + identity_hidden
        + "</form></section>"
    )


def _candidate_key(candidate: dict, index: int) -> str:
    raw = str(candidate.get("candidate_id") or f"candidate-{index}")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-")
    return safe or f"candidate-{index}"


def _candidate_page_label(candidate: dict) -> tuple[str, str]:
    if candidate.get("status") == "located" and candidate.get("highlighted_image_refs"):
        return _verified_page_summary(candidate)
    hint = candidate.get("retrieval_page_label")
    if hint:
        return "未核实页线索", str(hint)
    return "未定位原页", "当前只作为检索线索"


def _render_candidate_choice(candidate: dict, index: int, selected: bool) -> str:
    key = _candidate_key(candidate, index)
    status = str(candidate.get("status") or "")
    primary_page, _secondary = _candidate_page_label(candidate)
    selected_class = " selected" if selected else ""
    return (
        f"<div class='candidate-choice{selected_class}' data-candidate='{html.escape(key)}'>"
        "<div class='candidate-choice-main'>"
        f"<span class='state-label {_status_class(status)}'>{html.escape(_human_candidate_status(status))}</span>"
        f"<span class='candidate-page'>{html.escape(primary_page)}</span>"
        "<span class='current-mark'>当前查看</span></div>"
        f"<button type='button' onclick=\"selectCandidate('{html.escape(key)}')\">展开查看</button>"
        "</div>"
    )


def _render_detail_citations(candidate: dict, run_id: str) -> str:
    if candidate.get("status") != "located" or not candidate.get("highlighted_image_refs"):
        return "<div class='detail-empty'>这条候选尚未形成可回查的原页证据，因此暂不生成可复制引用。</div>"
    citation = _render_citation_output(candidate, run_id)
    return "<div class='citations-inline'>" + citation + "</div>"


def _render_candidate_detail(candidate: dict, index: int, run_id: str, active: bool) -> str:
    key = _candidate_key(candidate, index)
    status = str(candidate.get("status") or "")
    display = candidate.get("display_text") or candidate.get("original_text") or ""
    active_class = " active" if active else ""
    refs = candidate.get("highlighted_image_refs") or []
    if status == "located" and refs:
        gallery = (
            "<div class='detail-gallery'>"
            + "".join(
                "<img loading='lazy' src='/asset?run="
                + html.escape(run_id)
                + "&ref="
                + urllib.parse.quote(str(ref))
                + "' alt='一手文献原页高亮'>"
                for ref in refs
            )
            + "</div>"
        )
    else:
        hint = candidate.get("retrieval_page_label")
        gallery = (
            "<div class='detail-empty'>这条候选还没有稳定映射回 PDF 原页。"
            + (
                "<br>仅供继续查找的页面线索：" + html.escape(str(hint))
                if hint else ""
            )
            + "</div>"
        )
    return (
        f"<section class='detail-panel{active_class}' id='detail-{html.escape(key)}' data-detail='{html.escape(key)}'>"
        "<div class='detail-block'>" + gallery + "</div>"
        "<div class='detail-block'>"
        f"<div class='detail-text'>{html.escape(display or '当前没有可展示的候选原文。')}</div></div>"
        "<div class='detail-block'>"
        + _render_detail_citations(candidate, run_id)
        + "</div></section>"
    )


def _render_status_merge(state: dict, plausible_count: int) -> str:
    current = state.get("state")
    if current == mvp.STATE_MULTIPLE_CANDIDATES:
        return (
            "<div class='status-merge'><b>找到多个可能对应的段落</b>"
            f"<p>当前有 {plausible_count} 个已定位到原页的高相关候选。右侧默认展示第一条；"
            "点击下方候选可切换查看，默认展示不等于最终确认。</p></div>"
        )
    if current == mvp.STATE_EVIDENCE_FOUND:
        return (
            "<div class='status-merge'><b>已找到可回查的对应证据</b>"
            "<p>候选已定位到原页，可在右侧核对原页、高亮、原文和引用。</p></div>"
        )
    if current == mvp.STATE_NO_CORRESPONDING_PASSAGE:
        return (
            "<div class='status-merge'><b>暂未找到可靠对应证据</b>"
            "<p>下面的条目只作为继续排查的检索线索，不代表引用已核实。</p></div>"
        )
    return (
        "<div class='status-merge'><b>当前资料源不足以核验</b>"
        "<p>请更换可读取的 PDF；系统不会把资料不足误报成“文献不存在”。</p></div>"
    )


def render_result(
    run_id: str,
    result: dict,
    input_info: dict,
    run_input: dict | None = None,
) -> str:
    state = result["result_state"]
    candidates = result.get("candidates") or []
    plausible = _plausible_located_candidates(result)
    metadata = _result_metadata(result)

    if state["state"] == mvp.STATE_EVIDENCE_FOUND and plausible:
        visible = plausible[:1]
    elif state["state"] == mvp.STATE_MULTIPLE_CANDIDATES:
        visible = plausible
    else:
        visible = candidates[: min(len(candidates), 8)]

    visible_ids = {id(item) for item in visible}
    others = [item for item in candidates if id(item) not in visible_ids]
    selected = visible[0] if visible else (candidates[0] if candidates else None)

    body = [
        "<div class='result-workspace'>",
        "<div class='result-left-zone'>",
        "<div class='result-header'><h1 class='brand-title'><span class='brand-name'>二流文科生</span>的二手文献引用助手</h1></div>",
        _render_source_dropzone(result, run_input),
        "<div class='result-left-lower'>",
        "<aside class='result-meta'>",
        "<div class='panel-title'>书目信息</div>",
        "<div class='meta-card'>",
        _render_metadata_summary(metadata),
        "</div>",
        _render_compact_conflict(metadata),
        "</aside>",
        "<section class='result-candidates'>",
        _render_status_merge(state, len(plausible)),
        "<div class='candidate-list'>",
    ]

    for index, candidate in enumerate(visible):
        body.append(_render_candidate_choice(candidate, index, candidate is selected))
    body.append("</div>")

    if others:
        body.append(
            "<details class='other-candidates'><summary>"
            + html.escape(f"其他检索候选（{len(others)}）")
            + "</summary><div class='candidate-list'>"
        )
        start_index = len(visible)
        for offset, candidate in enumerate(others):
            body.append(_render_candidate_choice(candidate, start_index + offset, candidate is selected))
        body.append("</div></details>")
    body.append("</section></div></div>")

    body.append("<section class='result-detail'>")
    detail_candidates = visible + others
    if detail_candidates:
        for index, candidate in enumerate(detail_candidates):
            body.append(
                _render_candidate_detail(
                    candidate,
                    index,
                    run_id,
                    candidate is selected,
                )
            )
    else:
        body.append(
            "<div class='detail-panel active'><div class='detail-empty'>"
            "当前没有可展示的候选证据。可以从左上方更换一手 PDF 后重新运行。"
            "</div></div>"
        )
    body.append("</section></div>")

    body.append(
        "<script>"
        "function selectCandidate(key){"
        "document.querySelectorAll('.candidate-choice').forEach(function(el){"
        "el.classList.toggle('selected',el.dataset.candidate===key);});"
        "document.querySelectorAll('.detail-panel[data-detail]').forEach(function(el){"
        "el.classList.toggle('active',el.dataset.detail===key);});"
        "}"
        "var input=document.getElementById('source-swap-input');"
        "if(input){input.addEventListener('change',function(){if(this.files&&this.files.length){this.form.submit();}});}"
        "var drop=document.getElementById('source-swap-form');"
        "if(drop){['dragenter','dragover'].forEach(function(evt){drop.addEventListener(evt,function(e){e.preventDefault();drop.classList.add('drag');});});"
        "['dragleave','drop'].forEach(function(evt){drop.addEventListener(evt,function(){drop.classList.remove('drag');});});}"
        "</script>"
    )
    body.append("<p class='result-back'><a href='/'>← 返回重新输入</a></p>")
    return page("引用核验结果", "".join(body), main_class="result-page-main")


# --------------------------------------------------------------------------- #
# lawful open-source finder (post-MVP Phase 1, optional and reversible)
# --------------------------------------------------------------------------- #

ACCESS_LABEL_ZH = {
    sa.ACCESS_OPEN_PDF: "可直接下载的开放 PDF",
    sa.ACCESS_OPEN_PAGE: "开放全文（不是 PDF）",
    sa.ACCESS_METADATA_ONLY: "只有书目或预览",
    sa.ACCESS_USER_UPLOAD: "没有找到开放全文",
    sa.ACCESS_ERROR: "来源查询失败",
    sa.ACCESS_RATE_LIMIT: "来源被限流",
}

PROVIDER_LABEL_ZH = {
    "oapen": "OAPEN 开放获取图书库",
    "doab": "DOAB 开放获取图书目录",
    "openalex": "OpenAlex",
    "google_books": "Google Books",
    "internet_archive": "Internet Archive",
    "wikisource_zh": "中文维基文库",
}


def _finder_provider_line(report: list[dict]) -> str:
    parts = []
    for entry in report:
        name = PROVIDER_LABEL_ZH.get(str(entry.get("provider")), str(entry.get("provider")))
        if entry.get("ok"):
            parts.append(f"{name} ✓{entry.get('count', 0)}")
        else:
            parts.append(f"{name} ✗")
    return " ｜ ".join(parts) or "（没有查询任何来源）"


def _hidden(name: str, value: object) -> str:
    return f"<input type='hidden' name='{name}' value='{html.escape(str(value or ''))}'>"


def _identity_hidden(prefill: dict) -> str:
    """Serialise the confirmed identity so it survives the next continuation."""
    identity = prefill.get("identity") if isinstance(prefill, dict) else None
    if not identity:
        return ""
    return _hidden("identity_json", json.dumps(identity, ensure_ascii=False))


def _render_found_record(record: dict, index: int, token: str, prefill: dict) -> str:
    status = str(record.get("access_status"))
    title = str(record.get("title") or "（没有标题）")
    authors = "、".join(record.get("authors") or []) or "（作者未记录）"
    provider = PROVIDER_LABEL_ZH.get(
        str(record.get("source_provider")), str(record.get("source_provider"))
    )
    score = float(record.get("match_score") or 0.0)
    parts = [
        "<div class='card'>",
        f"<b>{html.escape(title)}</b><br>",
        f"<span class='tag'>{html.escape(provider)}</span>",
        f"<span class='tag'>{html.escape(ACCESS_LABEL_ZH.get(status, status))}</span>",
        f"<span class='tag'>与查询的重合度 {score:.2f}</span>",
        f"<div class='muted'>{html.escape(authors)} · {html.escape(str(record.get('year') or '年份未记录'))}</div>",
    ]
    if record.get("license"):
        parts.append(f"<div class='muted'>权利/许可：{html.escape(str(record['license']))}</div>")
    if record.get("landing_url"):
        url = str(record["landing_url"])
        parts.append(
            "<div class='muted'>来源页："
            f"<a href='{html.escape(url)}' target='_blank' rel='noreferrer'>"
            f"{html.escape(url[:110])}</a></div>"
        )
    if record.get("evidence_eligible"):
        parts.append(
            "<form method='post' action='/use_found'>"
            + _hidden("token", token)
            + _hidden("index", index)
            + _hidden("secondary_text", prefill.get("secondary_text"))
            + _hidden("footnote", prefill.get("footnote") or prefill.get("hints"))
            + _hidden("hints", prefill.get("hints"))
            + _identity_hidden(prefill)
            + "<button type='submit'>下载这个开放 PDF，并用它做核验 →</button></form>"
            "<p class='muted'>下载前会校验 PDF 文件头；文件只保存到本机 "
            "<code>data/private/</code>，并同时保存来源与许可记录。</p>"
        )
    else:
        reason = str(
            record.get("reason_not_evidence_eligible")
            or "不能作为页码可核验的一手证据"
        )
        parts.append(
            f"<div class='ocr'>不能作为页码可核验的一手证据：{html.escape(reason)}</div>"
        )
    parts.append("</div>")
    return "".join(parts)


def _identity_bundle_text(identity: dict) -> str:
    """A copyable "find this edition" string, built only from known fields."""
    work = identity.get("cited_work") or {}
    parts = [work.get("author"), work.get("title")]
    if identity.get("translator"):
        parts.append(f"{identity['translator']} 译")
    for container in identity.get("containing_publications") or []:
        if container.get("title") and container["title"] != work.get("title"):
            parts.append(f"收录于《{container['title']}》")
    if identity.get("publisher"):
        parts.append(str(identity["publisher"]))
    if work.get("year"):
        parts.append(f"{work['year']}年")
    if work.get("cited_page"):
        parts.append(f"第{work['cited_page']}页")
    identifiers = work.get("identifiers") or {}
    if identifiers.get("isbn"):
        parts.append(f"ISBN {identifiers['isbn']}")
    if identifiers.get("doi"):
        parts.append(f"DOI {identifiers['doi']}")
    return "，".join(str(part) for part in parts if part)


def _render_identity_card(identity: dict) -> str:
    description = fp.describe_identity(identity)
    rows = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>"
        for label, value in description["fields"]
    )
    if not rows:
        rows = "<tr><th>被引作品</th><td>还没有识别到可用的作者/题名</td></tr>"
    return (
        "<div class='card'><b>系统识别到的被引一手文献</b>"
        f"<p class='muted'>作品类型：{html.escape(description['work_type_label'])}。"
        "“被引作品（篇目）”与“收录它的中文出版物”是两件事，下面分开显示。</p>"
        f"<table>{rows}</table></div>"
    )


def render_identity(
    identity: dict,
    secondary_text: str,
    footnote: str,
    *,
    message: str = "",
) -> str:
    work = identity.get("cited_work") or {}
    identifiers = work.get("identifiers") or {}
    container = (identity.get("containing_publications") or [{}])[0]
    bundle = _identity_bundle_text(identity)
    provenance_rows = "".join(
        f"<tr><th>{html.escape(fp.FIELD_LABEL_ZH.get(key, key))}</th>"
        f"<td>{html.escape(str(value))}</td></tr>"
        for key, value in (identity.get("provenance") or {}).items()
        if value
    )
    unresolved = identity.get("unresolved") or []
    body = [
        "<h1>识别被引的一手文献</h1>",
        "<p class='sub'>下面只根据你给的脚注/尾注和二手文字提取线索，没有联网、也没有调用模型。"
        "请核对并按需要修改，再去找对应的中文出版物或开放全文。</p>",
        f"<div class='warn'>{html.escape(message)}</div>" if message else "",
        _render_identity_card(identity),
    ]
    body.append(
        "<div class='card'><b>核对或修改线索</b>"
        "<p class='muted'>留空表示“未能识别”。被引篇目和收录它的中文出版物请分开填写。</p>"
        "<form method='post' action='/find' enctype='multipart/form-data'>"
        + _hidden("secondary_text", secondary_text)
        + _hidden("footnote", footnote)
        + "<label>被引作品的作者</label>"
        + f"<input type='text' name='id_author' value='{html.escape(str(work.get('author') or ''))}'>"
        + "<label>被引篇名 / 书名（原文或译名均可）</label>"
        + f"<input type='text' name='id_title' value='{html.escape(str(work.get('title') or ''))}'>"
        + "<label>年份</label>"
        + f"<input type='text' name='id_year' value='{html.escape(str(work.get('year') or ''))}'>"
        + "<label>所引页码</label>"
        + f"<input type='text' name='id_cited_page' value='{html.escape(str(work.get('cited_page') or ''))}'>"
        + "<label>译者</label>"
        + f"<input type='text' name='id_translator' value='{html.escape(str(identity.get('translator') or ''))}'>"
        + "<label>出版社</label>"
        + f"<input type='text' name='id_publisher' value='{html.escape(str(identity.get('publisher') or ''))}'>"
        + "<label>可能收录它的中文出版物 / 文集</label>"
        + f"<input type='text' name='id_container_title' value='{html.escape(str(container.get('title') or ''))}'>"
        + "<label>DOI</label>"
        + f"<input type='text' name='id_doi' value='{html.escape(str(identifiers.get('doi') or ''))}'>"
        + "<label>ISBN</label>"
        + f"<input type='text' name='id_isbn' value='{html.escape(str(identifiers.get('isbn') or ''))}'>"
        + "<button type='submit'>确认并按脚注查找对应中文出版物 / 开放全文 →</button>"
        + "<p class='muted'>或者：我已经有对应的中文版 PDF。上传这份 PDF 会直接进入核验，"
        "不经过来源查找；上面修改过的书目信息会一并提交，不用重新填写。</p>"
        + "<label>我已有的一手文献 PDF</label>"
        + "<input type='file' name='primary_file' accept='.pdf'>"
        + _evidence_metadata_inputs()
        + "<button type='submit' formaction='/extract'>上传并用这份识别结果核验 →</button>"
        "</form></div>"
    )
    if provenance_rows:
        body.append(
            "<div class='card muted'><b>每个字段的来源</b><table>"
            + provenance_rows
            + "</table></div>"
        )
    if unresolved:
        body.append(
            "<p class='muted'>尚未识别的字段："
            + html.escape("、".join(str(item) for item in unresolved))
            + "。缺失的字段不会由系统凭空补全。</p>"
        )
    if bundle:
        bundle_id = "ident_bundle"
        body.append(
            "<div class='card'><b>查找这一版</b>（可复制，用于在图书馆/书店/知网等检索）"
            + _copy_button(bundle_id, "复制")
            + f"<pre id='{bundle_id}'>{html.escape(bundle)}</pre></div>"
        )
    return page("识别被引文献", "".join(body))


def _missing_minimum_handles(identity: dict) -> list[str]:
    """The minimum bibliographic handles a targeted lookup needs, still missing.

    A page number or "同上" is not enough to search on, so the retry page names
    exactly which of author / title / DOI / ISBN are still absent instead of
    silently rendering the same page again.
    """
    work = (identity or {}).get("cited_work") or {}
    identifiers = work.get("identifiers") or {}
    missing: list[str] = []
    if not work.get("title"):
        missing.append("篇名/书名")
    if not work.get("author"):
        missing.append("作者")
    if not identifiers.get("doi"):
        missing.append("DOI")
    if not identifiers.get("isbn"):
        missing.append("ISBN")
    return missing


def render_ask_more_clue(
    secondary_text: str, footnote: str, *, message: str = ""
) -> str:
    body = [
        "<h1>还需要一点脚注线索</h1>",
        "<p class='sub'>目前从你给的材料里还不足以确定被引的一手文献。"
        "定向查找只会基于作者、篇名/书名、DOI、ISBN 这类具体线索；"
        "线索不足时，产品不会退化成全网漫无目的的搜索。</p>",
        f"<div class='warn'>{html.escape(message)}</div>" if message else "",
        "<div class='card'><b>补充线索后重新识别</b>"
        "<p>① 在下面把脚注/尾注补全（作者、篇名或书名、年份、页码、译者、出版社）；<br>"
        "② 或者上传脚注截图，系统会用 RapidOCR 读取；<br>"
        "③ 或者直接上传你已有的中文版 PDF 核验。</p>"
        "<form method='post' action='/identify' enctype='multipart/form-data'>"
        + _hidden("secondary_text", secondary_text)
        + "<label>脚注 / 尾注（可编辑或补充）</label>"
        + f"<textarea name='footnote'>{html.escape(footnote)}</textarea>"
        + "<label>或上传脚注截图（自动 OCR）</label>"
        + "<input type='file' name='footnote_file' "
        "accept='.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff'>"
        + "<button type='submit'>我已补充脚注，重新识别 →</button>"
        "</form></div>",
        "<div class='card'><form method='post' action='/extract' enctype='multipart/form-data'>"
        + _hidden("secondary_text", secondary_text)
        + _hidden("footnote", footnote)
        + "<b>或者直接上传已有的一手文献 PDF 核验</b>"
        "<p class='muted'>上传后不经过来源查找，直接在 PDF 里定位原页。</p>"
        "<input type='file' name='primary_file' accept='.pdf'>"
        "<button type='submit'>上传一手文献 PDF，直接核验 →</button>"
        "</form></div>",
        "<p><a href='/'>← 返回</a></p>",
    ]
    return page("需要更多脚注线索", "".join(body))


def render_finder(payload: dict, token: str, prefill: dict, *, message: str = "") -> str:
    records = payload.get("results") or []
    outcome = payload.get("outcome") or {}
    identity = payload.get("identity") or {}
    # D024 safety gate: a record is shown as a source only when it is both
    # evidence-eligible and bibliographically relevant to the confirmed
    # identity. Everything else moves to a collapsed debug list so that an
    # unrelated but downloadable open PDF is never offered as a plausible choice.
    anchor = fp.identity_anchor(identity) if identity else None
    leads: list[tuple[int, dict]] = []
    weak: list[tuple[int, dict, str]] = []
    for index, record in enumerate(records):
        relevant, reason = sa.record_relevance(record, anchor)
        if relevant:
            leads.append((index, record))
        else:
            weak.append((index, record, reason))
    has_actionable_pdf = any(
        sa.record_actionable(record, anchor)[0] for _, record in leads
    )
    body = [
        "<h1>查找对应的中文出版物 / 开放全文</h1>",
        "<p class='sub'>这一步只在点击时联网，只用公开、免费、无需账号的接口"
        "（OpenAlex、Internet Archive、Google Books、中文维基文库）。"
        "不会绕过付费墙、登录、借阅或任何访问控制；非 PDF 的开放全文只能当线索，"
        "不能当作页码可核验的证据。</p>",
        f"<div class='warn'>{html.escape(message)}</div>" if message else "",
    ]
    if identity:
        body.append(_render_identity_card(identity))
    body.append(
        "<div class='card'>"
        f"<b>查询：</b>{html.escape(str(payload.get('query') or ''))}<br>"
        f"<b>结论：</b>{html.escape(str(outcome.get('message') or '没有查询'))}<br>"
        f"<span class='muted'>{html.escape(_finder_provider_line(payload.get('providers') or []))}</span>"
        "</div>"
    )
    if not records:
        body.append("<div class='card muted'>这次没有返回任何候选记录。</div>")
    for index, record in leads:
        body.append(_render_found_record(record, index, token, prefill))
    if identity and not has_actionable_pdf:
        bundle = _identity_bundle_text(identity)
        bundle_id = "finder_bundle"
        body.append(
            "<div class='card'><b>当前没有找到可直接使用的 PDF</b>"
            "<p class='muted'>没有找到与你确认的书目可信匹配的中文出版物或开放全文候选；"
            "仅因为“可以下载”而出现的不相关开放 PDF 不会被当作来源建议。"
            "这不代表这本文献不存在——已保留这份中文出版信息，你不必重新输入。"
            "可以复制下面这段去图书馆/书店/数据库查找，或直接上传你合法获得的 PDF。</p>"
            + _copy_button(bundle_id, "复制“查找这一版”")
            + f"<pre id='{bundle_id}'>{html.escape(bundle)}</pre></div>"
        )
    if weak:
        weak_rows = "".join(
            "<li>"
            + html.escape(str(record.get("title") or "（没有标题）"))
            + " · "
            + html.escape(
                PROVIDER_LABEL_ZH.get(
                    str(record.get("source_provider")), str(record.get("source_provider"))
                )
            )
            + f" · 与查询的重合度 {float(record.get('match_score') or 0.0):.2f}"
            + " · "
            + html.escape(reason)
            + "</li>"
            for _index, record, reason in weak
        )
        body.append(
            "<details class='dev'><summary>开发者 / 调试：本次未采用的记录"
            "（不构成来源建议）</summary><div>"
            "<p class='muted'>以下记录没有通过书目安全校验，因此不提供下载或核验入口；"
            "它们只是调试信息，不代表这本文献不存在。</p>"
            f"<ul>{weak_rows}</ul></div></details>"
        )
    if payload.get("query"):
        body.append(
            "<div class='card'><form method='post' action='/find'>"
            + _hidden("secondary_text", prefill.get("secondary_text"))
            + _hidden("footnote", prefill.get("footnote") or prefill.get("hints"))
            + _hidden("hints", prefill.get("hints"))
            + _hidden("find_query", payload.get("query"))
            + _identity_hidden(prefill)
            + "<button type='submit' class='ghost'>重新查找一次（不重新输入线索）</button>"
            "</form></div>"
        )
    body.append(
        "<div class='card'><form method='post' action='/extract' enctype='multipart/form-data'>"
        + "<b>上传你已有的中文版 PDF，直接核验</b>"
        + "<p class='muted'>上传后不经过来源查找，直接在 PDF 里定位原页；"
        "上面的书目信息和检索文本会一并保留，不用重新填写。</p>"
        + _hidden("secondary_text", prefill.get("secondary_text"))
        + _hidden("footnote", prefill.get("footnote") or prefill.get("hints"))
        + _hidden("hints", prefill.get("hints"))
        + _identity_hidden(prefill)
        + "<input type='file' name='primary_file' accept='.pdf'>"
        + "<button type='submit'>上传并用这份识别结果核验 →</button>"
        "</form></div>"
    )
    return page("查找对应中文出版物", "".join(body))


def guess_query_from_text(text: str) -> str:
    """Fallback query when the user searched without typing one."""
    for line in (text or "").splitlines():
        line = line.strip()
        if line:
            return line[:120]
    return ""


def render_error(message: str) -> str:
    return page(
        "出错了",
        f"<h1>出错了</h1><div class='banner b-none'>{html.escape(message)}</div>"
        "<p><a href='/'>← 返回</a></p>",
    )


# --------------------------------------------------------------------------- #
# jobs
# --------------------------------------------------------------------------- #


JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def _register_job(job_id: str, out_dir: Path) -> dict:
    job = {"status": "running", "log": [], "out_dir": out_dir, "started": time.time()}
    with JOBS_LOCK:
        JOBS[job_id] = job
    return job


def run_job(
    job_id: str,
    *,
    secondary_text: str,
    hints: str,
    source: dict,
    options: dict,
    confirmed_identity: dict | None = None,
) -> None:
    job = JOBS[job_id]
    out_dir = job["out_dir"]

    def log(message: str) -> None:
        job["log"].append(f"[{time.strftime('%H:%M:%S')}] {message}")

    try:
        log(f"开始：来源 {source.get('source_id')}，检索深度 k={options['k']}")
        log("扫描文本层 / 确认检索路径 …")
        result = mvp.run_pipeline(
            secondary_text=secondary_text,
            hints=hints,
            source=source,
            confirmed_identity=confirmed_identity,
            out_dir=out_dir,
            retrieval_mode="local",
            ocr_mode=options["ocr_mode"],
            k=options["k"],
            log=log,
        )
        log(
            f"完成：状态 {result['result_state']['state']}，"
            f"候选 {result['counts']['candidates']}，已定位 {result['counts']['located']}"
        )
        job["status"] = "done"
    # SystemExit is caught as well: the pipeline reports user-facing validation
    # problems that way, and a bare SystemExit would otherwise escape the worker
    # thread and leave the job stuck at "running" forever.
    except (Exception, SystemExit) as error:  # noqa: BLE001 - surfaced, never hidden
        job["status"] = "error"
        job["error"] = f"{type(error).__name__}: {error}" + NL + traceback.format_exc()
        log("运行失败")


# --------------------------------------------------------------------------- #
# HTTP layer
# --------------------------------------------------------------------------- #


def parse_multipart(body: bytes, boundary: bytes) -> list[tuple[str, str | None, bytes]]:
    fields: list[tuple[str, str | None, bytes]] = []
    for chunk in body.split(b"--" + boundary):
        if not chunk or chunk.startswith(b"--"):
            continue
        if chunk.startswith(CRLF):
            chunk = chunk[len(CRLF):]
        if chunk.endswith(CRLF):
            chunk = chunk[: -len(CRLF)]
        head, separator, data = chunk.partition(CRLFCRLF)
        if not separator:
            continue
        headers = head.decode("utf-8", "replace")
        match = re.search(r'name="([^"]*)"', headers)
        if not match:
            continue
        filename = re.search(r'filename="([^"]*)"', headers)
        fields.append((match.group(1), filename.group(1) if filename else None, data))
    return fields


def parse_form(headers, body: bytes) -> list[tuple[str, str | None, bytes]]:
    content_type = headers.get("Content-Type", "")
    if content_type.startswith("multipart/form-data"):
        match = re.search(r"boundary=([^;]+)", content_type)
        if not match:
            return []
        boundary = match.group(1).strip().strip('"').encode("utf-8")
        return parse_multipart(body, boundary)
    parsed = urllib.parse.parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True)
    return [(key, None, value[0].encode("utf-8")) for key, value in parsed.items()]


def field(fields: list[tuple[str, str | None, bytes]], name: str, default: str = "") -> str:
    values = [data.decode("utf-8", "replace").strip() for key, _fn, data in fields if key == name]
    return values[-1] if values else default


def field_all(fields: list[tuple[str, str | None, bytes]], name: str) -> list[str]:
    return [data.decode("utf-8", "replace").strip() for key, _fn, data in fields if key == name]


def file_field(
    fields: list[tuple[str, str | None, bytes]], name: str
) -> tuple[str, bytes] | None:
    for key, filename, data in fields:
        if key == name and filename:
            return filename, data
    return None


class InputError(Exception):
    """A user-facing input problem; the message is shown as text, never a traceback."""


def save_upload(
    fields: list[tuple[str, str | None, bytes]], name: str, target_dir: Path
) -> Path | None:
    """Write one uploaded file below ``data/private/`` and return its path."""
    upload = file_field(fields, name)
    if not upload:
        return None
    filename, data = upload
    if not data:
        return None
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / Path(filename).name
    target.write_bytes(data)
    return target


def extract_uploaded_text(
    fields: list[tuple[str, str | None, bytes]], name: str, work_dir: Path
) -> dict | None:
    """Save one uploaded secondary/note screenshot or PDF and read its text.

    Returns ``None`` when no file was attached, so an empty file input never
    overwrites the pasted text. Reuses the same text-layer / RapidOCR helper as
    the rest of the product: there is no separate OCR subsystem.
    """
    if file_field(fields, name) is None:
        return None
    saved = save_upload(fields, name, work_dir)
    if saved is None:
        return None
    return extract_secondary_text(upload_path=saved, work_dir=work_dir)


def identity_json_field(fields: list[tuple[str, str | None, bytes]]) -> dict | None:
    """Read the confirmed-identity hidden field that carries state across routes."""
    raw = field(fields, "identity_json")
    if not raw:
        return None
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def evidence_metadata_from_fields(
    fields: list[tuple[str, str | None, bytes]], *, document_id: str | None = None
) -> dict:
    """Collect user-confirmed metadata for the PDF that supplies page evidence."""
    metadata: dict[str, str] = {}
    for key, _label in EVIDENCE_METADATA_FIELDS:
        value = field(fields, f"evidence_{key}").strip()
        if value:
            metadata[key] = value
    if not metadata:
        return {}
    if document_id:
        metadata["document_id"] = document_id
    metadata["metadata_origin"] = "用户确认（上传的一手 PDF 版本信息）"
    return metadata


def resolve_run_source(
    fields: list[tuple[str, str | None, bytes]], sources: list[dict], uploads_dir: Path
) -> dict:
    """Decide which primary source a web run will use, or raise ``InputError``.

    Precedence: an uploaded primary PDF, then the advanced local path, then the
    registered demo/cached source. An uploaded file may only come from this
    machine's upload directory, so a form field cannot point the run at an
    arbitrary file. Every choice is validated before a job starts.
    """
    primary_upload = field(fields, "primary_upload")
    primary_metadata = field(fields, "primary_metadata")
    source_path = field(fields, "source_path")
    metadata_path = field(fields, "metadata_path")

    if primary_upload:
        path = Path(primary_upload)
        if not path.is_absolute():
            path = REPO_ROOT / path
        resolved = path.resolve()
        try:
            resolved.relative_to(Path(uploads_dir).resolve())
        except ValueError:
            raise InputError("上传的一手文献不在本次上传目录中，已拒绝使用这个路径。")
        source = {
            "source_id": resolved.stem,
            "label": f"上传的一手文献 PDF：{resolved.name}",
            "pdf": str(resolved),
            "metadata": primary_metadata or metadata_path or "",
            "docname": resolved.stem,
        }
    elif source_path:
        source = {
            "source_id": Path(source_path).stem,
            "label": f"自定义本地 PDF：{Path(source_path).name}",
            "pdf": source_path,
            "metadata": metadata_path,
            "docname": Path(source_path).stem,
        }
    else:
        try:
            source = dict(mvp.find_source(sources, field(fields, "source")))
        except SystemExit as error:
            raise InputError(str(error))
        if metadata_path:
            source["metadata"] = metadata_path

    problem = mvp.describe_source_problem(source)
    if problem:
        raise InputError(problem)
    return source


def asset_target(runs_dir: Path, run_id: str, ref: str) -> Path | None:
    """Resolve a page-image reference, refusing anything outside the run dir.

    The product serves original-page PNGs over localhost, so a request may only
    read a file that is really below ``data/private/mvp_runs/<run_id>/``.
    """
    out_dir = (Path(runs_dir) / run_id).resolve()
    target = (REPO_ROOT / ref).resolve()
    try:
        target.relative_to(out_dir)
    except ValueError:
        return None
    return target


class Handler(BaseHTTPRequestHandler):
    server_version = "citation-verifier-mvp"
    sources: list[dict] = []
    finder_dir: Path = mvp.DEFAULT_CACHE_DIR / "finder"
    runs_dir = mvp.DEFAULT_RUNS_DIR
    uploads_dir = mvp.DEFAULT_UPLOADS_DIR

    # -- helpers ---------------------------------------------------------- #

    def _send(
        self,
        content: bytes,
        content_type: str = "text/html; charset=utf-8",
        code: int = 200,
    ) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[http] " + (fmt % args) + NL)

    # -- routes ----------------------------------------------------------- #

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._send(render_form(self.sources).encode("utf-8"))
            return
        if parsed.path == "/asset":
            self._serve_asset(urllib.parse.parse_qs(parsed.query))
            return
        if parsed.path.startswith("/job/"):
            job_id = parsed.path.split("/", 2)[2]
            job = JOBS.get(job_id)
            if not job:
                self._send(render_error("找不到这个运行任务").encode("utf-8"), code=404)
                return
            self._send(render_job(job_id, job).encode("utf-8"))
            return
        if parsed.path.startswith("/result/"):
            self._serve_result(parsed.path.split("/", 2)[2])
            return
        self._send(render_error("未知路径").encode("utf-8"), code=404)

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_UPLOAD_BYTES:
            self._send(render_error("上传文件过大").encode("utf-8"), code=413)
            return
        body = self.rfile.read(length) if length else b""
        fields = parse_form(self.headers, body)
        if parsed.path == "/extract":
            self._handle_extract(fields)
            return
        if parsed.path == "/identify":
            self._handle_identify(fields)
            return
        if parsed.path == "/run":
            self._handle_run(fields)
            return
        if parsed.path == "/rerun_source":
            self._handle_rerun_source(fields)
            return
        if parsed.path == "/find":
            self._handle_find(fields)
            return
        if parsed.path == "/use_found":
            self._handle_use_found(fields)
            return
        self._send(render_error("未知路径").encode("utf-8"), code=404)

    # -- lawful source finder --------------------------------------------- #

    IDENTITY_OVERRIDE_FIELDS = (
        "author",
        "title",
        "year",
        "cited_page",
        "translator",
        "publisher",
        "container_title",
        "doi",
        "isbn",
    )

    def _identity_from_request(self, fields) -> tuple[dict, dict]:
        """Rebuild the confirmed identity from the editable confirmation form.

        The confirmation screen posts ``id_*`` edits, which always win; any
        later continuation instead re-posts the serialised identity so the
        user's confirmed fields survive without re-entry.
        """
        secondary_text = field(fields, "secondary_text")
        footnote = field(fields, "footnote") or field(fields, "hints")
        identity = self._carried_identity(fields) or fp.build_identity(
            footnote, secondary_text
        )
        prefill = {
            "secondary_text": secondary_text,
            "footnote": footnote,
            "hints": field(fields, "hints"),
        }
        if identity:
            prefill["identity"] = identity
        return identity, prefill

    def _id_overrides(self, fields) -> dict | None:
        """Every ``id_*`` field present in the request, blanks included.

        Presence, not truthiness, is what matters: the confirmation screen always
        posts all its visible fields, so an empty string means the user
        deliberately cleared a wrong parsed value. ``None`` means the request
        carries no ``id_*`` fields at all (a later continuation re-posts
        ``identity_json`` instead).
        """
        posted = {key for key, _filename, _data in fields}
        overrides: dict[str, str] = {}
        for key in self.IDENTITY_OVERRIDE_FIELDS:
            name = f"id_{key}"
            if name in posted:
                overrides[key] = field(fields, name)
        return overrides or None

    def _carried_identity(self, fields) -> dict | None:
        """Confirmed identity carried into a route beyond the confirmation screen."""
        overrides = self._id_overrides(fields)
        if overrides is not None:
            return fp.build_identity(
                field(fields, "footnote") or field(fields, "hints"),
                field(fields, "secondary_text"),
                overrides=overrides,
            )
        return identity_json_field(fields)

    def _handle_identify(self, fields: list[tuple[str, str | None, bytes]]) -> None:
        """Footnote-first Stage 2/3: parse the note, show editable candidates."""
        secondary_text = field(fields, "secondary_text")
        footnote = field(fields, "footnote") or field(fields, "hints")
        work_dir = self.uploads_dir / time.strftime("%Y%m%d-%H%M%S") / "identify"
        try:
            # P0-A: the advertised secondary screenshot/PDF input must be read
            # here too, not only pasted text, or the passage is silently lost.
            secondary_info = extract_uploaded_text(
                fields, "secondary_file", work_dir / "secondary"
            )
            note_info = extract_uploaded_text(
                fields, "footnote_file", work_dir / "footnote"
            )
        except Exception as error:  # noqa: BLE001 - shown, never a traceback
            self._send(
                render_error(f"读取上传内容失败：{error}").encode("utf-8"), code=500
            )
            return
        if secondary_info is not None and (secondary_info.get("text") or "").strip():
            secondary_text = (secondary_info.get("text") or "").strip()
        if note_info is not None and (note_info.get("text") or "").strip():
            footnote = (note_info.get("text") or "").strip()
        if not secondary_text.strip() and not footnote.strip():
            self._send(
                render_form(
                    self.sources,
                    message="请至少粘贴二手文献文字，或对应的脚注 / 尾注。",
                ).encode("utf-8")
            )
            return
        identity = fp.build_identity(footnote, secondary_text)
        if not fp.identity_is_useful(identity):
            # Stage 4/8.8: no concrete handle -> ask for a better clue, never
            # launch a broad whole-web search.
            message = ""
            if footnote.strip():
                # P1-J: a real retry that still carries no usable handle must
                # visibly say so, instead of looking like a dead button.
                missing = "、".join(_missing_minimum_handles(identity))
                message = (
                    "仍然没能从这段脚注里读出可用的书目线索："
                    f"{missing or '作者、篇名/书名、DOI、ISBN'} 都还没识别出来。"
                    "定向查找至少需要其中之一；请把脚注补全，或直接上传你已有的中文版 PDF。"
                )
            self._send(
                render_ask_more_clue(secondary_text, footnote, message=message).encode("utf-8")
            )
            return
        self._send(render_identity(identity, secondary_text, footnote).encode("utf-8"))

    def _handle_find(self, fields: list[tuple[str, str | None, bytes]]) -> None:
        identity, prefill = self._identity_from_request(fields)
        prefill["identity"] = identity
        explicit = field(fields, "find_query").strip()
        if explicit:
            query = explicit
        else:
            queries = fp.identity_queries(identity)
            query = queries[0] if queries else ""
        if not query:
            self._send(
                render_form(
                    self.sources,
                    message="请先填写要查找的书名、作者、ISBN 或 DOI。",
                    prefill=prefill,
                ).encode("utf-8")
            )
            return
        try:
            payload = dict(
                sa.search_all(
                    query,
                    limit=FINDER_RESULT_LIMIT,
                    anchor=fp.identity_anchor(identity),
                )
            )
        except Exception as error:  # noqa: BLE001 - shown, never a traceback
            payload = {
                "query": query,
                "providers": [],
                "outcome": {"status": sa.ACCESS_ERROR, "message": f"查询失败：{error}"},
                "results": [],
            }
            payload["identity"] = identity
            self._send(
                render_finder(
                    payload,
                    "",
                    prefill,
                    message="查询开放来源时出错。已保留书目识别结果，"
                    "可以稍后重试，或直接上传你合法获得的 PDF。",
                ).encode("utf-8")
            )
            return
        payload["identity"] = identity
        token = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
        self.finder_dir.mkdir(parents=True, exist_ok=True)
        (self.finder_dir / f"{token}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._send(render_finder(payload, token, prefill).encode("utf-8"))

    def _handle_use_found(self, fields: list[tuple[str, str | None, bytes]]) -> None:
        token = field(fields, "token")
        secondary_text = field(fields, "secondary_text")
        hints = field(fields, "hints")
        footnote = field(fields, "footnote") or hints
        prefill = {"secondary_text": secondary_text, "hints": hints, "footnote": footnote}
        try:
            index = int(field(fields, "index") or -1)
        except ValueError:
            index = -1

        payload = None
        if FINDER_TOKEN_RE.fullmatch(token or ""):
            candidate = self.finder_dir / f"{token}.json"
            if candidate.exists():
                try:
                    payload = json.loads(candidate.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    payload = None
        records = (payload or {}).get("results") or []
        identity = (payload or {}).get("identity") or identity_json_field(fields)
        if identity:
            prefill["identity"] = identity
        if payload is None or not 0 <= index < len(records):
            self._send(
                render_form(
                    self.sources,
                    message="这次查找结果已经失效，请重新查找，或者直接上传你合法获得的 PDF。",
                    prefill=prefill,
                ).encode("utf-8")
            )
            return
        record = records[index]
        anchor = fp.identity_anchor(identity) if identity else None
        actionable, reason = sa.record_actionable(record, anchor)
        if not actionable:
            self._send(
                render_finder(
                    payload,
                    token,
                    prefill,
                    message=f"这条记录不能自动下载：{reason}。",
                ).encode("utf-8")
            )
            return

        work_dir = self.uploads_dir / time.strftime("%Y%m%d-%H%M%S") / "primary"
        try:
            saved = sa.download_open_pdf(record, work_dir)
        except (sa.DownloadRefused, sa.ProviderError) as error:
            self._send(
                render_finder(
                    payload, token, prefill, message=f"下载失败：{error}"
                ).encode("utf-8")
            )
            return
        saved_path = Path(saved["path"])
        sa.write_provenance(saved, saved_path.with_suffix(".provenance.json"))
        prefill["primary_upload"] = mvp.repo_relative(saved_path)
        notes = [
            f"已从 {PROVIDER_LABEL_ZH.get(str(record.get('source_provider')), record.get('source_provider'))}"
            f"下载开放 PDF：{saved_path.name}（{saved['bytes']} 字节，"
            f"sha256 {str(saved['sha256'])[:12]}…）。",
            "请人工确认这份 PDF 就是你引用的那本文献；来源与许可已记录在同目录的 "
            f"{saved_path.with_suffix('.provenance.json').name}。",
        ]
        if not secondary_text.strip():
            notes.append("还没填写二手文献文本：请把引用或转述粘贴到下面的文本框再检索。")
        info = {
            "origin": "found_open_pdf",
            "file": saved_path.name,
            "notes": notes,
            "text": secondary_text,
            "ocr_pages": 0,
            "text_chars": len(secondary_text),
        }
        prefill["_sources"] = self.sources
        self._send(render_confirm(info, prefill).encode("utf-8"))

    # -- handlers --------------------------------------------------------- #

    def _handle_extract(self, fields: list[tuple[str, str | None, bytes]]) -> None:
        prefill = {
            "secondary_text": field(fields, "secondary_text"),
            "hints": field(fields, "hints"),
            "footnote": field(fields, "footnote") or field(fields, "hints"),
            "source": field(fields, "source"),
            "source_path": field(fields, "source_path"),
            "metadata_path": field(fields, "metadata_path"),
            "primary_upload": field(fields, "primary_upload"),
            "primary_metadata": field(fields, "primary_metadata"),
            "k": field(fields, "k", "10"),
            "ocr_mode": field(fields, "ocr_mode", "auto"),
        }
        identity = self._carried_identity(fields)
        if identity:
            prefill["identity"] = identity
        work_dir = self.uploads_dir / time.strftime("%Y%m%d-%H%M%S")
        upload_path = save_upload(fields, "secondary_file", work_dir)
        # P0-B: the footnote/endnote screenshot is the main navigation clue even
        # on the owned-PDF path, so read it here instead of dropping it.
        try:
            note_info = extract_uploaded_text(
                fields, "footnote_file", work_dir / "footnote"
            )
        except Exception as error:  # noqa: BLE001 - shown, never a traceback
            self._send(
                render_error(f"读取脚注截图失败：{error}").encode("utf-8"), code=500
            )
            return
        if note_info is not None and (note_info.get("text") or "").strip():
            prefill["footnote"] = (note_info.get("text") or "").strip()
        primary_upload = file_field(fields, "primary_file")
        if primary_upload is not None:
            # Validate the uploaded primary source before the run, so an EPUB or
            # a non-PDF gets the explicit Chinese explanation instead of a
            # traceback (or a wasted upload) later.
            problem = mvp.primary_format_problem(primary_upload[0])
            primary_path = None
            if not problem:
                primary_path = save_upload(fields, "primary_file", work_dir / "primary")
                if primary_path is not None:
                    problem = mvp.describe_source_problem({"pdf": str(primary_path)})
            if problem or primary_path is None:
                self._send(
                    render_form(
                        self.sources,
                        message="上传的一手文献无法使用："
                        + (problem or "上传的文件是空的，请重新选择。"),
                        prefill=prefill,
                    ).encode("utf-8")
                )
                return
            prefill["primary_upload"] = mvp.repo_relative(primary_path)
            evidence_metadata = evidence_metadata_from_fields(
                fields, document_id=primary_path.stem
            )
            if evidence_metadata:
                primary_metadata_path = primary_path.with_suffix(".metadata.json")
                primary_metadata_path.write_text(
                    json.dumps(evidence_metadata, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                prefill["primary_metadata"] = mvp.repo_relative(primary_metadata_path)
        try:
            info = extract_secondary_text(
                pasted=prefill["secondary_text"],
                upload_path=upload_path,
                work_dir=work_dir,
            )
        except Exception as error:  # noqa: BLE001
            self._send(
                render_error(f"读取二手文献内容失败：{error}").encode("utf-8"), code=500
            )
            return
        if not (info.get("text") or "").strip():
            message = "没能从这次输入里读到可用文字，请直接粘贴文本或换一个文件。"
            self._send(
                render_form(self.sources, message=message, prefill=prefill).encode("utf-8")
            )
            return
        if prefill.get("primary_upload"):
            info["notes"].append(
                "一手文献使用你刚上传的 PDF："
                + Path(prefill["primary_upload"]).name
            )
        prefill["_sources"] = self.sources
        self._send(render_confirm(info, prefill).encode("utf-8"))

    def _handle_rerun_source(self, fields: list[tuple[str, str | None, bytes]]) -> None:
        secondary_text = field(fields, "secondary_text")
        hints = field(fields, "footnote") or field(fields, "hints")
        upload = file_field(fields, "primary_file")
        if not secondary_text.strip():
            self._send(render_error("当前核验文本为空，无法重新运行。").encode("utf-8"), code=400)
            return
        if upload is None:
            self._send(render_error("请选择新的 PDF。").encode("utf-8"), code=400)
            return

        problem = mvp.primary_format_problem(upload[0])
        if problem:
            self._send(render_error("新的来源文件无法使用：" + problem).encode("utf-8"), code=400)
            return

        work_dir = (
            self.uploads_dir
            / (time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2))
            / "primary"
        )
        primary_path = save_upload(fields, "primary_file", work_dir)
        if primary_path is None:
            self._send(render_error("没有收到新的 PDF 文件。").encode("utf-8"), code=400)
            return
        problem = mvp.describe_source_problem({"pdf": str(primary_path)})
        if problem:
            self._send(render_error("新的来源文件无法使用：" + problem).encode("utf-8"), code=400)
            return

        source = {
            "source_id": primary_path.stem,
            "label": f"上传的一手文献 PDF：{primary_path.name}",
            "pdf": str(primary_path),
            "metadata": "",
            "docname": primary_path.stem,
        }
        try:
            k = max(1, min(50, int(field(fields, "k", "12") or 12)))
        except ValueError:
            k = 12
        options = {
            "k": k,
            "ocr_mode": field(fields, "ocr_mode", "auto") or "auto",
        }
        confirmed_identity = identity_json_field(fields)
        run_id = time.strftime("web-%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
        out_dir = self.runs_dir / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        input_info = {"origin": "result_source_swap", "file": primary_path.name}
        (out_dir / "input.json").write_text(
            json.dumps(
                {
                    "secondary_text": secondary_text,
                    "hints": hints,
                    "source": source,
                    "options": options,
                    "input_info": input_info,
                    "confirmed_identity": confirmed_identity,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        _register_job(run_id, out_dir)
        threading.Thread(
            target=run_job,
            args=(run_id,),
            kwargs={
                "secondary_text": secondary_text,
                "hints": hints,
                "source": source,
                "options": options,
                "confirmed_identity": confirmed_identity,
            },
            daemon=True,
        ).start()
        self._redirect(f"/job/{run_id}")

    def _handle_run(self, fields: list[tuple[str, str | None, bytes]]) -> None:
        secondary_text = field(fields, "secondary_text")
        selected = field_all(fields, "item")
        if selected:
            try:
                items = json.loads(field(fields, "items_json") or "[]")
                chosen = [
                    items[int(index)]
                    for index in selected
                    if index.isdigit() and int(index) < len(items)
                ]
            except Exception:  # noqa: BLE001 - fall back to the edited text
                chosen = []
            if chosen:
                secondary_text = NL.join(chosen)
        if not secondary_text.strip():
            self._send(render_error("检索文本为空").encode("utf-8"), code=400)
            return

        try:
            source = resolve_run_source(fields, self.sources, self.uploads_dir)
        except InputError as error:
            prefill = {
                "secondary_text": secondary_text,
                "hints": field(fields, "hints"),
                "footnote": field(fields, "footnote") or field(fields, "hints"),
                "source": field(fields, "source"),
                "source_path": field(fields, "source_path"),
                "metadata_path": field(fields, "metadata_path"),
                "k": field(fields, "k", "10"),
                "ocr_mode": field(fields, "ocr_mode", "auto") or "auto",
            }
            identity = identity_json_field(fields)
            if identity:
                prefill["identity"] = identity
            self._send(
                render_form(
                    self.sources, message="一手文献无法使用：" + str(error), prefill=prefill
                ).encode("utf-8")
            )
            return

        try:
            k = max(1, min(50, int(field(fields, "k", "10") or 10)))
        except ValueError:
            k = 10
        options = {"k": k, "ocr_mode": field(fields, "ocr_mode", "auto") or "auto"}
        input_info = {
            "origin": field(fields, "secondary_origin", "pasted"),
            "file": field(fields, "secondary_file") or None,
        }
        # The footnote/endnote is the primary navigation clue, so it drives the
        # hint-assisted retrieval pass; the legacy free-form hints still apply.
        hints = field(fields, "footnote") or field(fields, "hints")
        # Confirmed bibliographic identity, carried from /identify or the finder
        # continuation, feeds the citation metadata honestly (see P0-C).
        confirmed_identity = identity_json_field(fields)
        run_id = time.strftime("web-%Y%m%d-%H%M%S")
        out_dir = self.runs_dir / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "input.json").write_text(
            json.dumps(
                {
                    "secondary_text": secondary_text,
                    "hints": hints,
                    "source": source,
                    "options": options,
                    "input_info": input_info,
                    "confirmed_identity": confirmed_identity,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        _register_job(run_id, out_dir)
        threading.Thread(
            target=run_job,
            args=(run_id,),
            kwargs={
                "secondary_text": secondary_text,
                "hints": hints,
                "source": source,
                "options": options,
                "confirmed_identity": confirmed_identity,
            },
            daemon=True,
        ).start()
        self._redirect(f"/job/{run_id}")

    def _serve_result(self, run_id: str) -> None:
        out_dir = self.runs_dir / run_id
        result_path = out_dir / "result.json"
        if not result_path.exists():
            self._send(render_error("这个运行还没有结果").encode("utf-8"), code=404)
            return
        result = json.loads(result_path.read_text(encoding="utf-8"))
        input_path = out_dir / "input.json"
        run_input = (
            json.loads(input_path.read_text(encoding="utf-8"))
            if input_path.exists()
            else {}
        )
        input_info = run_input.get("input_info", {})
        self._send(render_result(run_id, result, input_info, run_input).encode("utf-8"))

    def _serve_asset(self, query: dict) -> None:
        run_id = (query.get("run") or [""])[0]
        ref = (query.get("ref") or [""])[0]
        target = asset_target(self.runs_dir, run_id, ref)
        if target is None:
            self._send(b"forbidden", "text/plain; charset=utf-8", code=403)
            return
        if not target.exists() or target.suffix.lower() != ".png":
            self._send(b"missing", "text/plain; charset=utf-8", code=404)
            return
        self._send(target.read_bytes(), "image/png")


def serve(host: str, port: int) -> None:
    Handler.sources = mvp.load_sources()
    Handler.runs_dir = mvp.DEFAULT_RUNS_DIR
    Handler.uploads_dir = mvp.DEFAULT_UPLOADS_DIR
    Handler.finder_dir = mvp.DEFAULT_CACHE_DIR / "finder"
    Handler.runs_dir.mkdir(parents=True, exist_ok=True)
    Handler.uploads_dir.mkdir(parents=True, exist_ok=True)
    Handler.finder_dir.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"二手文献引用助手（MVP 完成 + 后 MVP 补丁）已启动： http://{host}:{port}")
    print("仅监听本机地址；所有数据保存在 data/private/ 下。按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(NL + "已停止。")
    finally:
        server.server_close()


# --------------------------------------------------------------------------- #
# headless single run
# --------------------------------------------------------------------------- #


def run_once(args: argparse.Namespace) -> int:
    sources = mvp.load_sources(args.sources)
    if args.source_path:
        source = {
            "source_id": Path(args.source_path).stem,
            "label": f"自定义本地 PDF：{Path(args.source_path).name}",
            "pdf": args.source_path,
            "metadata": args.metadata_path or "",
            "docname": Path(args.source_path).stem,
        }
    else:
        source = dict(mvp.find_source(sources, args.source))
    problem = mvp.describe_source_problem(source)
    if problem:
        raise SystemExit(problem)
    secondary_text = args.secondary_text
    if args.secondary_file:
        info = extract_secondary_text(
            upload_path=Path(args.secondary_file),
            work_dir=mvp.DEFAULT_UPLOADS_DIR / "run-once",
        )
        if not secondary_text:
            secondary_text = info["text"]
        print(
            json.dumps(
                {key: value for key, value in info.items() if key != "text"},
                ensure_ascii=False,
                indent=2,
            )
        )
    if not secondary_text:
        raise SystemExit("--secondary-text or --secondary-file is required")
    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else mvp.DEFAULT_RUNS_DIR / time.strftime("once-%Y%m%d-%H%M%S")
    )
    result = mvp.run_pipeline(
        secondary_text=secondary_text,
        hints=args.hints,
        source=source,
        out_dir=out_dir,
        retrieval_mode="local",
        ocr_mode=args.ocr_mode,
        k=args.k,
        log=lambda message: print(f"[run] {message}", flush=True),
    )
    print(
        json.dumps(
            {
                "result_state": result["result_state"]["state"],
                "result_state_label_zh": result["result_state"]["label_zh"],
                "source": result["source"]["source_id"],
                "route": result["source"]["route"],
                "counts": result["counts"],
                "run": result["run"],
                "out_dir": mvp.repo_relative(out_dir),
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--sources", type=Path, default=mvp.DEFAULT_SOURCES)
    parser.add_argument("--run-once", action="store_true", help="run one query and exit")
    parser.add_argument("--secondary-text", default="")
    parser.add_argument("--secondary-file", default=None)
    parser.add_argument("--hints", default="")
    parser.add_argument("--source", default=None)
    parser.add_argument("--source-path", default=None)
    parser.add_argument("--metadata-path", default=None)
    parser.add_argument("--ocr-mode", choices=("auto", "off", "force"), default="auto")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)

    if args.run_once:
        if args.source is None and args.source_path is None:
            raise SystemExit("--run-once needs --source or --source-path")
        return run_once(args)

    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

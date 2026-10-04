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
:root{--ink:#1b1b1b;--muted:#5b6470;--line:#d9dee5;--bg:#f7f8fa;--card:#fff;
--ok:#1e7a3c;--warn:#b26a00;--bad:#b3261e;--info:#2f5d9e;}
*{box-sizing:border-box}
body{font-family:system-ui,"Microsoft YaHei","PingFang SC",sans-serif;color:var(--ink);
background:var(--bg);margin:0;line-height:1.65}
main{max-width:1080px;margin:0 auto;padding:24px 18px 64px}
h1{font-size:22px;margin:0 0 4px}
h2{font-size:17px;margin:28px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
h3{font-size:15px;margin:14px 0 4px}
.sub{color:var(--muted);font-size:13px;margin:0 0 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:12px 0}
.banner{border-radius:10px;padding:14px 16px;margin:14px 0;border-left:6px solid}
.banner b{display:block;font-size:15px;margin-bottom:2px}
.b-evidence{background:#e9f5ec;border-color:var(--ok)}
.b-multiple{background:#eef3fb;border-color:var(--info)}
.b-none{background:#fdf0e6;border-color:var(--warn)}
.b-insufficient{background:#f2f3f5;border-color:#6b7280}
.chip{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;color:#fff;
vertical-align:middle}
.located{background:var(--ok)}.ambiguous{background:var(--warn)}
.unmatched{background:var(--bad)}.needs-ocr{background:#4b5563}
.tag{display:inline-block;padding:1px 7px;border:1px solid var(--line);border-radius:8px;
font-size:12px;color:var(--muted);background:#fff;margin-right:6px}
.warn{background:#fff8e1;border-left:4px solid #ffb300;padding:8px 10px;margin:8px 0;font-size:13px}
.ocr{background:#eef7ff;border-left:4px solid var(--info);padding:8px 10px;margin:8px 0;font-size:13px}
table{border-collapse:collapse;width:100%;font-size:13px;margin:6px 0}
td,th{border:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}
th{background:#fafbfc;width:190px;font-weight:600}
pre{white-space:pre-wrap;background:#f6f7f9;border:1px solid var(--line);border-radius:8px;
padding:10px;font-family:inherit;font-size:14px;margin:8px 0}
textarea,input[type=text],input[type=number],input[type=file],select{width:100%;padding:8px;
border:1px solid var(--line);border-radius:8px;font-family:inherit;font-size:14px;background:#fff}
textarea{min-height:120px}
label{display:block;font-weight:600;font-size:13px;margin:14px 0 4px}
button{background:#22303f;color:#fff;border:0;border-radius:8px;padding:9px 16px;font-size:14px;
cursor:pointer;margin-top:12px}
button.ghost{background:#fff;color:#22303f;border:1px solid var(--line);padding:5px 10px;
font-size:12px;margin:0}
button.ghost.right{float:right}
img{max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:8px}
details{border:1px solid var(--line);border-radius:10px;background:var(--card);margin:10px 0}
details>summary{cursor:pointer;padding:12px 14px;font-size:14px;font-weight:600;list-style:none}
details>summary::-webkit-details-marker{display:none}
details>div{padding:0 14px 14px}
details.dev{background:#fbfbfd;border-style:dashed}
details.dev>summary{color:var(--muted);font-size:13px;font-weight:500}
.muted{color:var(--muted);font-size:13px}
.log{font-family:ui-monospace,Consolas,monospace;font-size:12px;background:#0f1720;color:#d7e2ee;
padding:12px;border-radius:8px;max-height:320px;overflow:auto;white-space:pre-wrap}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.hint{font-weight:400;display:block;margin:4px 0}
@media(max-width:720px){.grid{grid-template-columns:1fr}}
"""


def _chip(status: str) -> str:
    css = STATUS_STYLE.get(status, "unmatched")
    return f"<span class='chip {css}'>{html.escape(status)}</span>"


def _copy_button(target_id: str, label: str = "复制") -> str:
    return (
        f"<button class='ghost right' type='button' "
        f"onclick=\"navigator.clipboard.writeText("
        f"(document.getElementById('{target_id}').value "
        f"|| document.getElementById('{target_id}').textContent))\">"
        f"{html.escape(label)}</button>"
    )


def page(title: str, body: str) -> str:
    return (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
        f"<body><main>{body}</main></body></html>"
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


def _render_candidate(candidate: dict, run_id: str) -> str:
    refs = candidate.get("highlighted_image_refs") or []
    metadata = candidate.get("bibliographic_metadata") or {}
    tags = [
        f"<span class='tag'>PDF 页 {candidate.get('pdf_page_numbers') or '—'}</span>",
        f"<span class='tag'>检索位次 {candidate.get('retrieval_rank')}</span>",
    ]
    if candidate.get("retrieval_score") is not None:
        tags.append(f"<span class='tag'>相似度 {candidate['retrieval_score']}</span>")
    if candidate.get("retrieved_with") == "hints":
        tags.append("<span class='tag'>线索补充召回</span>")
    summary = (
        f"{candidate['candidate_id']} " + "".join(tags) + _chip(candidate["status"])
    )
    parts = [f"<details><summary>{summary}</summary><div>"]

    # 1) The Chinese primary text the user actually came for.
    original = candidate.get("original_text") or ""
    display = candidate.get("display_text") or original
    text_id = f"text_{run_id}_{candidate['candidate_id']}"
    parts.append("<h3>对应中文版原文</h3>")
    parts.append(_copy_button(text_id, "复制原文"))
    parts.append(f"<textarea id='{text_id}' readonly>{html.escape(display)}</textarea>")
    removed = candidate.get("display_text_removed_lines") or []
    if removed:
        parts.append(
            "<p class='muted'>显示时隐藏了页面边缘的重复噪声标记："
            + html.escape("、".join(removed))
            + "（原始检索文本与高亮范围未改动）。</p>"
        )

    # 2) The highlighted original page + page provenance.
    printed = candidate.get("printed_page_numbers")
    page_show = printed or candidate.get("pdf_page_numbers") or "—"
    parts.append("<h3>原页高亮与页码</h3>")
    parts.append(
        "<p class='muted'>页码：" + html.escape(str(page_show)) + "。"
        + ("已确认印刷页码；PDF 顺序页仍保留在上方标签。" if printed else "未确认印刷页码，这里给出 PDF 顺序页；产品不会用 PDF 页号冒充印刷页码。")
        + "</p>"
    )
    for ref in refs:
        parts.append(
            "<div><img src='/asset?run="
            + html.escape(run_id)
            + "&ref="
            + urllib.parse.quote(ref)
            + "' alt='原页高亮'></div>"
        )
    if not refs:
        parts.append("<p class='muted'>该候选没有生成高亮图像（状态不是 located）。</p>")

    # 3) Bibliographic metadata (only confirmed fields are shown).
    hidden_keys = (
        "document_id",
        "metadata_origin",
        "metadata_provenance",
        "metadata_conflicts",
        "chinese_edition_confirmed",
    )
    known = {
        key: value
        for key, value in metadata.items()
        if value not in (None, "", []) and key not in hidden_keys
    }
    parts.append("<h3>书目信息</h3><table>")
    for key, value in known.items():
        parts.append(
            f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
        )
    parts.append(
        f"<tr><th>元数据来源</th><td>"
        f"{html.escape(str(metadata.get('metadata_origin') or '—'))}</td></tr>"
    )
    parts.append("</table>")
    provenance = metadata.get("metadata_provenance") or {}
    if provenance:
        parts.append(
            "<p class='muted'>每个书目字段的来源："
            + "；".join(
                f"{html.escape(str(key))} = {html.escape(str(value))}"
                for key, value in provenance.items()
            )
            + "。</p>"
        )
    conflicts = metadata.get("metadata_conflicts") or {}
    for key, detail in conflicts.items():
        if not isinstance(detail, dict):
            continue
        parts.append(
            f"<div class='warn'>书目冲突：{html.escape(str(key))} —— "
            f"证据 PDF 记录为“{html.escape(str(detail.get('source_record')))}”，"
            f"二手脚注 / 确认线索为“{html.escape(str(detail.get('confirmed')))}”；"
            f"本次证据引用采用“{html.escape(str(detail.get('used')))}”，另一条主张继续保留供核查。</div>"
        )

    # 4) One-click Chinese citation output.
    footnote_id = f"fn_{run_id}_{candidate['candidate_id']}"
    reference_id = f"rf_{run_id}_{candidate['candidate_id']}"
    parts.append("<h3>一键复制引用</h3><table>")
    if candidate.get("basic_footnote_citation"):
        parts.append(
            f"<tr><th>脚注（基础）</th><td>{_copy_button(footnote_id, '复制脚注')}"
            f"<pre id='{footnote_id}'>"
            f"{html.escape(candidate['basic_footnote_citation'])}</pre></td></tr>"
        )
        parts.append(
            f"<tr><th>参考文献（基础）</th><td>{_copy_button(reference_id, '复制参考文献')}"
            f"<pre id='{reference_id}'>"
            f"{html.escape(candidate['basic_reference_citation'])}</pre></td></tr>"
        )
    else:
        hint = ""
        if metadata.get("chinese_edition_confirmed") is False:
            hint = (
                "（尚未确认对应的中文出版物：外文原作不会被自动当成中文版引用，"
                "请确认或补充中文版信息。）"
            )
        parts.append(
            "<tr><th>引用</th><td>缺少已确认的元数据，未生成引用串。"
            + hint
            + "</td></tr>"
        )
    parts.append("</table>")

    # 5) Retrieval/evidence detail kept out of the way by default.
    parts.append("<details class='dev'><summary>检索与证据细节</summary><div><table>")
    parts.append(
        f"<tr><th>PDF 顺序页</th><td>{candidate.get('pdf_page_numbers') or '—'}</td></tr>"
        "<tr><th>印刷页码</th><td>"
        + (
            html.escape(str(printed))
            if printed
            else "未确认（不会用 PDF 页号顶替）"
        )
        + "</td></tr>"
        f"<tr><th>检索页标签</th><td>{html.escape(str(candidate.get('retrieval_page_label')))}</td></tr>"
        "<tr><th>证据来源</th><td>"
        + (
            "OCR 识别文本（需与页面图像核对）"
            if candidate.get("evidence_origin") == "ocr"
            else "PDF 文本层"
        )
        + "</td></tr></table></div></details>"
    )

    unresolved = candidate.get("unresolved_fields") or []
    if unresolved:
        parts.append(
            "<p class='muted'>未确认字段："
            + html.escape("、".join(str(field) for field in unresolved))
            + "</p>"
        )
    for warning in candidate.get("warnings", []):
        css = "ocr" if "RapidOCR" in warning else "warn"
        parts.append(f"<div class='{css}'>{html.escape(warning)}</div>")
    parts.append("</div></details>")
    return "".join(parts)


def render_result(run_id: str, result: dict, input_info: dict) -> str:
    state = result["result_state"]
    state_class, state_title = STATE_STYLE[state["state"]]
    run = result["run"]
    counts = result["counts"]
    source = result["source"]
    route_label = {
        "text_layer": "PDF 文本层（默认路径）",
        "ocr": "RapidOCR 扫描识别（可选路径）",
        "unavailable": "不可用",
    }.get(source.get("route"), str(source.get("route")))
    body = [
        "<h1>检索结果</h1>",
        f"<p class='sub'>一手来源：{html.escape(source['label'])}</p>",
        f"<div class='banner b-{state_class}'><b>{html.escape(state_title)}</b>"
        f"{html.escape(state['label_zh'])}<br>"
        f"<span class='muted'>{html.escape(state['explanation_zh'])}</span></div>",
    ]
    if source.get("route") == "ocr":
        body.append(
            "<div class='ocr'>本次来源是扫描本，文字来自 RapidOCR 机器识别。"
            "OCR 文本不是出版社文本层，引用前必须与页面图像核对；本产品不公布字符准确率。</div>"
        )
    if source.get("route") == "unavailable":
        body.append(
            "<div class='warn'>该来源当前无法检索：既没有可用文本层，也没有 OCR 缓存。"
            "这不是“文献不存在”的结论，而是“当前资料源不足以核验”。</div>"
        )

    body.append(f"<h2>候选段落（{counts['candidates']}）</h2>")
    if not result["candidates"]:
        body.append("<p class='muted'>没有候选段落。</p>")
    for candidate in result["candidates"]:
        body.append(_render_candidate(candidate, run_id))

    body.append("<details class='dev'><summary>本次运行与调试信息</summary><div>")
    body.append("<h3>本次运行</h3><table>")
    rows = [
        ("一手文献来源", f"{source['source_id']}（{source['label']}）"),
        ("检索路径", route_label),
        ("PDF 页数", source.get("page_count")),
        ("分块数", run.get("chunk_count")),
        ("检索方式", run.get("retrieval")),
        ("嵌入模型（本地）", run.get("embedding")),
        ("候选段落数", counts["candidates"]),
        ("已定位并可高亮", counts["located"]),
        ("高亮原页图像", counts["highlight_images"]),
        ("模型调用 / 成本", f"{run.get('model_calls')} 次 / ${run.get('cost_usd')}"),
        (
            "耗时（索引/检索/证据）",
            f"{run.get('index_seconds')}s / {run.get('retrieval_seconds')}s / "
            f"{run.get('evidence_seconds')}s",
        ),
        ("二手输入来源", input_info.get("origin")),
    ]
    for key, value in rows:
        body.append(f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>")
    body.append("</table>")

    body.append("<h3>二手文献输入（只作为线索，从不作为证据）</h3>")
    body.append(f"<pre>{html.escape(result.get('secondary_text') or '')}</pre>")
    if result.get("hints"):
        body.append(
            "<p class='muted'>线索（可能出错，只用于补充召回）：</p>"
            f"<pre>{html.escape(result['hints'])}</pre>"
        )

    body.append(
        "<h3>四种结果状态</h3><div class='card muted'>"
        "<p>1. 找到可靠对应证据（已定位到原页并高亮）；</p>"
        "<p>2. 找到多个可能对应的段落，并列展示，不强制选出唯一答案；</p>"
        "<p>3. 当前来源可以检索，但没有可靠的对应段落；</p>"
        "<p>4. 当前资料源无法提供足够的可检索一手文本（例如没有文本层也没有 OCR 缓存）。</p>"
        "<p>产品不会为了让结果好看而制造匹配。</p></div>"
    )
    body.append("</div></details>")
    body.append("<p><a href='/'>← 再查一条</a></p>")
    return page("检索结果", "".join(body))


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
        input_info = (
            json.loads(input_path.read_text(encoding="utf-8")).get("input_info", {})
            if input_path.exists()
            else {}
        )
        self._send(render_result(run_id, result, input_info).encode("utf-8"))

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

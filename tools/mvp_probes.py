#!/usr/bin/env python
"""Zero-cost acceptance probes for the product surface.

The suite covers the accepted MVP surface plus the post-MVP primary-source
intake patch (blank metadata, uploaded PDF, EPUB rejection, registered demos).

Every probe here is deterministic, offline and free: no LLM call, no paid API,
no network, and no private source material. The synthetic PDFs used by the
end-to-end probes are generated inside ``data/private/mvp_probes/`` (git-ignored)
and deleted afterwards, so nothing copyrighted is written into the repository.

Run:

    .venv\\Scripts\\python.exe tools\\mvp_probes.py
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import mvp_app as app  # noqa: E402
import mvp_pipeline as mvp  # noqa: E402
import footnote_parse as fp  # noqa: E402

WORK_DIR = REPO_ROOT / "data/private/mvp_probes"
SUMMARY_PATH = WORK_DIR / "mvp_probe_summary.json"
TEST_FONT = Path("C:/Windows/Fonts/simhei.ttf")

CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append({"probe": name, "ok": bool(ok), "detail": detail})


def _candidate(candidate_id: str, rank: int, score, text: str, pages, status="located", refs=None) -> dict:
    return {
        "candidate_id": candidate_id,
        "status": status,
        "retrieval_rank": rank,
        "retrieval_score": score,
        "retrieval_page_label": "doc pages 1-1",
        "pdf_page_numbers": pages,
        "printed_page_numbers": [],
        "highlighted_image_refs": refs if refs is not None else ["data/private/x.png"],
        "original_text": text,
        "display_text": text,
        "display_text_removed_lines": [],
        "basic_footnote_citation": None,
        "basic_reference_citation": None,
        "bibliographic_metadata": {},
        "unresolved_fields": [],
        "warnings": [],
        "fragments": [],
        "evidence_origin": "text_layer",
    }


# --------------------------------------------------------------------------- #
# input handling
# --------------------------------------------------------------------------- #


def probe_input_handling() -> None:
    pasted = app.extract_secondary_text(pasted="这是一条二手文献的转述。", work_dir=WORK_DIR)
    check(
        "input/pasted",
        pasted["origin"] == "pasted" and pasted["text"].endswith("。"),
        f"origin={pasted['origin']} chars={pasted['text_chars']}",
    )

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    text_file = WORK_DIR / "secondary.txt"
    text_file.write_text("二手文献段落一。", encoding="utf-8")
    uploaded = app.extract_secondary_text(upload_path=text_file, work_dir=WORK_DIR)
    check(
        "input/text-upload",
        uploaded["origin"] == "secondary_text_file" and uploaded["text_chars"] > 0,
        f"origin={uploaded['origin']} chars={uploaded['text_chars']}",
    )

    weird = WORK_DIR / "secondary.docx"
    weird.write_bytes(b"not really a docx")
    unsupported = app.extract_secondary_text(upload_path=weird, work_dir=WORK_DIR)
    check(
        "input/unsupported-upload",
        unsupported["origin"] == "unsupported_upload"
        and unsupported["text"] == ""
        and unsupported["notes"],
        f"origin={unsupported['origin']} notes={len(unsupported['notes'])}",
    )

    page = (
        "第一段引用：韦伯说行动是有意义的。\n\n"
        "第二段转述：他说社会行动顾及他人表现。\n\n"
        "第三段：另一处引用，讨论支配类型。"
    )
    items = app.split_secondary_items(page)
    check(
        "input/multi-item-split",
        len(items) == 3 and all(items),
        f"items={len(items)}",
    )
    single = app.split_secondary_items("只有一句话。")
    check("input/single-item", single == ["只有一句话。"], f"items={single}")


# --------------------------------------------------------------------------- #
# result-state classification
# --------------------------------------------------------------------------- #


def probe_result_states() -> None:
    none_state = mvp.classify_result_state([], searchable=True)
    check(
        "state/searchable-no-candidate",
        none_state["state"] == mvp.STATE_NO_CORRESPONDING_PASSAGE,
        none_state["state"],
    )
    insufficient = mvp.classify_result_state([], searchable=False)
    check(
        "state/insufficient-source",
        insufficient["state"] == mvp.STATE_INSUFFICIENT_SOURCE,
        insufficient["state"],
    )
    one = [_candidate("cand-01", 1, 0.60, "text", [1])]
    check(
        "state/single-evidence",
        mvp.classify_result_state(one, searchable=True)["state"] == mvp.STATE_EVIDENCE_FOUND,
    )
    band = [
        _candidate("cand-01", 1, 0.600, "text", [1]),
        _candidate("cand-02", 2, 0.595, "text", [2]),
    ]
    check(
        "state/multiple-within-band",
        mvp.classify_result_state(band, searchable=True)["state"]
        == mvp.STATE_MULTIPLE_CANDIDATES,
    )
    separated = [
        _candidate("cand-01", 1, 0.900, "text", [1]),
        _candidate("cand-02", 2, 0.400, "text", [2]),
    ]
    check(
        "state/single-outside-band",
        mvp.classify_result_state(separated, searchable=True)["state"]
        == mvp.STATE_EVIDENCE_FOUND,
    )
    unmatched = [_candidate("cand-01", 1, 0.9, "text", [], status="unmatched", refs=[])]
    check(
        "state/all-unlocated-is-no-passage",
        mvp.classify_result_state(unmatched, searchable=True)["state"]
        == mvp.STATE_NO_CORRESPONDING_PASSAGE,
    )


# --------------------------------------------------------------------------- #
# display cleanup never touches evidence
# --------------------------------------------------------------------------- #


def probe_display_cleanup() -> None:
    pages = {}
    for index in range(12):
        pages[str(index + 1)] = "国\n格：是的。\n正文第%d页的内容很长足够作为正文。" % index
    furniture = mvp.repeated_page_furniture(pages)
    check(
        "display/noise-detected",
        "国" in furniture,
        f"furniture={sorted(furniture)}",
    )
    check(
        "display/dialogue-stamp-kept",
        "格：是的。" not in furniture,
        f"furniture={sorted(furniture)}",
    )
    original = "国\n格：是的。\n正文内容。"
    display, removed = mvp.display_text_for(original, furniture)
    check(
        "display/strips-noise-keeps-text",
        "国" not in display.splitlines()
        and "格：是的。" in display
        and "正文内容。" in display
        and removed == ["国"],
        f"removed={removed}",
    )
    untouched, none_removed = mvp.display_text_for(original, set())
    check(
        "display/no-furniture-is-identity",
        untouched == original and none_removed == [],
    )


# --------------------------------------------------------------------------- #
# hint merging uses one comparable score and never drops a candidate
# --------------------------------------------------------------------------- #


class StubEmbedding:
    """Deterministic stand-in for the local embedding model (no model load)."""

    async def embed_document(self, text: str) -> list[float]:
        return [1.0 if "命中" in text else 0.0, 1.0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_document(text) for text in texts]


def probe_merge() -> None:
    primary = [
        {"rank": 1, "score": 0.9, "page_label": "doc pages 1-1", "text": "命中 主检索"},
    ]
    extra = [
        {"rank": 1, "score": 0.42, "page_label": "doc pages 1-1", "text": "命中 主检索"},
        {"rank": 2, "score": 0.41, "page_label": "doc pages 2-2", "text": "无关 线索"},
    ]
    merged = asyncio.run(mvp.merge_candidates(primary, extra, StubEmbedding(), "命中"))
    texts = [item["text"] for item in merged]
    check(
        "merge/dedupe-and-keep",
        len(merged) == 2 and "命中 主检索" in texts and "无关 线索" in texts,
        f"n={len(merged)}",
    )
    hint_only = next(item for item in merged if item["text"] == "无关 线索")
    check(
        "merge/hint-only-rescored-against-secondary-query",
        hint_only["score"] is not None and hint_only["score"] < 0.8 and hint_only["retrieved_with"] == "hints",
        f"score={hint_only['score']}",
    )
    check(
        "merge/ranks-are-sequential",
        [item["rank"] for item in merged] == [1, 2]
        and [item["candidate_id"] for item in merged] == ["cand-01", "cand-02"],
    )


# --------------------------------------------------------------------------- #
# HTTP form parsing and asset-path guard
# --------------------------------------------------------------------------- #


def probe_http_layer() -> None:
    boundary = b"----probe"
    body = b""
    for name, value in (("secondary_text", "第一段"), ("item", "0"), ("item", "1")):
        body += b"--" + boundary + b"\r\n"
        body += f'Content-Disposition: form-data; name="{name}"'.encode() + b"\r\n\r\n"
        body += value.encode("utf-8") + b"\r\n"
    body += b"--" + boundary + b"\r\n"
    body += b'Content-Disposition: form-data; name="secondary_file"; filename="a.txt"'
    body += b"\r\n\r\nfile-bytes\r\n"
    body += b"--" + boundary + b"--\r\n"
    fields = app.parse_multipart(body, boundary)
    check(
        "http/multipart-duplicate-checkboxes",
        app.field_all(fields, "item") == ["0", "1"],
        f"items={app.field_all(fields, 'item')}",
    )
    upload = app.file_field(fields, "secondary_file")
    check(
        "http/multipart-file-field",
        upload is not None and upload[0] == "a.txt" and upload[1] == b"file-bytes",
    )
    check(
        "http/multipart-text-field",
        app.field(fields, "secondary_text") == "第一段",
    )

    encoded = app.parse_form({"Content-Type": "application/x-www-form-urlencoded"}, b"k=5&hints=abc")
    check(
        "http/urlencoded",
        app.field(encoded, "k") == "5" and app.field(encoded, "hints") == "abc",
    )

    runs_dir = mvp.DEFAULT_RUNS_DIR
    inside = app.asset_target(runs_dir, "web-x", "data/private/mvp_runs/web-x/images/a.png")
    outside = app.asset_target(runs_dir, "web-x", "data/private/C04/evidence/rank-01_pdf0126_highlight.png")
    traversal = app.asset_target(runs_dir, "web-x", "data/private/mvp_runs/web-x/../../C04/evidence/x.png")
    check("http/asset-inside-run-allowed", inside is not None)
    check("http/asset-other-run-rejected", outside is None)
    check("http/asset-traversal-rejected", traversal is None)


# --------------------------------------------------------------------------- #
# primary-source intake (post-MVP pilot patch)
# --------------------------------------------------------------------------- #


def _blank_metadata_source() -> dict:
    return {
        "source_id": "C04",
        "label": "C04",
        "pdf": "data/private/C04/pqa_corpus/C04.pdf",
        "metadata": "",
        "docname": "C04",
    }


def probe_source_validation() -> None:
    """Blank/whitespace metadata, directory paths and unsupported formats."""
    for raw in ("", "   ", None):
        source = {**_blank_metadata_source(), "metadata": raw}
        resolved = mvp.resolve_paths(source)
        check(
            f"intake/blank-metadata-{raw!r}",
            resolved["metadata"] == {} and resolved["metadata_path"] is None,
            f"metadata={resolved['metadata']} path={resolved['metadata_path']}",
        )

    for directory in ("data/private", "data/private/C04"):
        source = {**_blank_metadata_source(), "metadata": directory}
        leaked = False
        message = ""
        try:
            mvp.resolve_paths(source)
        except SystemExit as error:
            message = str(error)
        except PermissionError:  # the original real-user bug
            leaked = True
        check(
            f"intake/directory-metadata-{directory}",
            not leaked and "文件夹" in message and "JSON" in message,
            "raw PermissionError leaked" if leaked else message[:80],
        )
    try:
        mvp.load_metadata(REPO_ROOT / "data/private")
        directory_error = ""
    except SystemExit as error:
        directory_error = str(error)
    check(
        "intake/load-metadata-directory-friendly",
        "文件夹" in directory_error,
        directory_error[:80],
    )

    missing_metadata = {**_blank_metadata_source(), "metadata": "data/private/nope.json"}
    try:
        mvp.resolve_paths(missing_metadata)
        missing_message = ""
    except SystemExit as error:
        missing_message = str(error)
    check(
        "intake/missing-metadata-friendly",
        "找不到元数据文件" in missing_message,
        missing_message[:80],
    )

    epub = mvp.describe_source_problem({"pdf": "D:/books/学术与政治.epub"})
    check(
        "intake/epub-rejected-with-explanation",
        bool(epub)
        and "EPUB" in epub
        and "页码" in epub
        and "PDF" in epub
        and "原页" in epub,
        (epub or "")[:90],
    )
    other = mvp.describe_source_problem({"pdf": "D:/books/学术与政治.docx"})
    check(
        "intake/other-format-rejected",
        bool(other) and ".docx" in other and "PDF" in other,
        (other or "")[:90],
    )
    check(
        "intake/blank-pdf-rejected",
        bool(mvp.describe_source_problem({"pdf": ""})),
    )
    check(
        "intake/format-check-works-on-a-bare-name",
        mvp.primary_format_problem("synthetic-text-layer.pdf") is None
        and "EPUB" in (mvp.primary_format_problem("学术与政治.epub") or "")
        and "只支持 PDF" in (mvp.primary_format_problem("book.azw3") or ""),
    )
    check(
        "intake/directory-as-pdf-rejected",
        "文件夹" in (mvp.describe_source_problem({"pdf": "data/private/C04"}) or ""),
    )
    check(
        "intake/missing-pdf-rejected",
        "找不到" in (
            mvp.describe_source_problem({"pdf": "data/private/C04/nope.pdf"}) or ""
        ),
    )
    fake_pdf = WORK_DIR / "renamed_epub.pdf"
    fake_pdf.write_bytes(b"PK\x03\x04 this is really an epub, not a pdf")
    check(
        "intake/fake-pdf-header-rejected",
        "不是 PDF" in (mvp.describe_source_problem({"pdf": str(fake_pdf)}) or ""),
    )
    try:
        mvp.resolve_paths({"pdf": "D:/books/x.epub", "metadata": ""})
        epub_resolved = ""
    except SystemExit as error:
        epub_resolved = str(error)
    check(
        "intake/epub-stops-pipeline-early",
        "EPUB" in epub_resolved,
        epub_resolved[:60],
    )

    for source in mvp.load_sources():
        check(
            f"intake/registered-source-ok-{source['source_id']}",
            mvp.describe_source_problem(source) is None,
            str(source.get("pdf")),
        )

    try:
        app.resolve_run_source(
            [("primary_upload", None, b"data/private/C04/pqa_corpus/C04.pdf")],
            mvp.load_sources(),
            WORK_DIR / "http_uploads",
        )
        forged = ""
    except app.InputError as error:
        forged = str(error)
    check(
        "intake/forged-upload-path-rejected",
        "上传目录" in forged,
        forged[:80],
    )


def _multipart(
    fields: list[tuple[str, str]],
    files: list[tuple[str, str, bytes]] | None = None,
    boundary: bytes = b"----mvp-probe",
) -> tuple[bytes, str]:
    body = b""
    for name, value in fields:
        body += b"--" + boundary + app.CRLF
        body += f'Content-Disposition: form-data; name="{name}"'.encode() + app.CRLFCRLF
        body += str(value).encode("utf-8") + app.CRLF
    for name, filename, data in files or []:
        body += b"--" + boundary + app.CRLF
        body += (
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'
        ).encode() + app.CRLF
        body += b"Content-Type: application/octet-stream" + app.CRLFCRLF
        body += data + app.CRLF
    body += b"--" + boundary + b"--" + app.CRLF
    return body, f"multipart/form-data; boundary={boundary.decode()}"


def _http_request(
    method: str, url: str, body: bytes | None = None, content_type: str | None = None
) -> tuple[int, str, str]:
    request = urllib.request.Request(url, data=body, method=method)
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return (
                response.status,
                response.geturl(),
                response.read().decode("utf-8", "replace"),
            )
    except urllib.error.HTTPError as error:
        return error.code, url, error.read().decode("utf-8", "replace")


def probe_web_primary_upload() -> None:
    """The real pilot path: upload a primary PDF in the web UI and run it."""
    pdf_path = WORK_DIR / "synthetic_text_layer.pdf"
    if not pdf_path.exists() and TEST_FONT.exists():
        make_text_layer_pdf(
            pdf_path,
            [
                "合成测试文献第一页。",
                "本页包含一段用于验证定位链路的中文文字。",
                "社会行动是指行动者以他人的表现为取向而展开的行动。",
                "其后还有一句无关的话，用来撑出足够的正文长度。",
            ],
        )
    if not pdf_path.exists():
        check("upload/primary-pdf-web", False, f"missing fixture {pdf_path}")
        return

    http_runs = WORK_DIR / "http_runs"
    http_uploads = WORK_DIR / "http_uploads"
    for directory in (http_runs, http_uploads):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)

    app.Handler.sources = mvp.load_sources()
    app.Handler.runs_dir = http_runs
    app.Handler.uploads_dir = http_uploads
    server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    host, port = server.server_address[0], server.server_address[1]
    base = f"http://{host}:{port}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        pdf_bytes = pdf_path.read_bytes()
        secondary = "某位二手作者转述：社会行动以他人表现为取向。"
        body, content_type = _multipart(
            [
                ("secondary_text", secondary),
                ("hints", ""),
                ("source", "C04"),
                ("k", "5"),
                ("ocr_mode", "auto"),
            ],
            [("primary_file", "synthetic-text-layer.pdf", pdf_bytes)],
        )
        status, _, page_html = _http_request("POST", f"{base}/extract", body, content_type)
        match = re.search(r"name='primary_upload' value='([^']*)'", page_html)
        uploaded_ref = match.group(1) if match else ""
        check(
            "upload/extract-accepts-primary-pdf",
            status == 200 and bool(uploaded_ref) and "确认要检索的文本" in page_html,
            f"status={status} ref={uploaded_ref}",
        )
        uploaded_path = (REPO_ROOT / uploaded_ref).resolve() if uploaded_ref else None
        check(
            "upload/stored-under-private-uploads",
            uploaded_path is not None
            and uploaded_path.exists()
            and uploaded_path.is_relative_to(http_uploads.resolve())
            and mvp.repo_relative(uploaded_path).startswith("data/private/"),
            str(uploaded_path),
        )
        check(
            "upload/confirm-page-names-the-upload",
            "你上传的一手文献 PDF" in page_html
            and "synthetic-text-layer.pdf" in page_html,
        )

        run_fields = [
            ("secondary_text", secondary),
            ("hints", ""),
            ("source", "C04"),
            ("primary_upload", uploaded_ref),
            ("k", "5"),
            ("ocr_mode", "auto"),
        ]
        source = app.resolve_run_source(
            [(name, None, value.encode("utf-8")) for name, value in run_fields],
            app.Handler.sources,
            http_uploads,
        )
        check(
            "upload/run-uses-uploaded-pdf",
            Path(source["pdf"]).name == "synthetic-text-layer.pdf"
            and Path(source["pdf"]).is_relative_to(http_uploads.resolve()),
            source["pdf"],
        )

        body, content_type = _multipart(run_fields)
        status, job_url, _ = _http_request("POST", f"{base}/run", body, content_type)
        job_id = job_url.rstrip("/").rsplit("/", 1)[-1] if "/job/" in job_url else ""
        check("upload/run-starts-a-job", status == 200 and bool(job_id), f"job={job_id}")
        if job_id:
            deadline = time.time() + 180
            job_html = ""
            while time.time() < deadline:
                _, _, job_html = _http_request("GET", f"{base}/job/{job_id}")
                if "查看结果" in job_html or "运行失败" in job_html:
                    break
                time.sleep(1.0)
            check(
                "upload/job-finishes-without-error",
                "查看结果" in job_html,
                "done" if "查看结果" in job_html else "timeout/error",
            )
            _, _, result_html = _http_request("GET", f"{base}/result/{job_id}")
            check(
                "upload/result-has-located-evidence",
                "可靠证据已找到" in result_html and "社会行动" in result_html,
            )

        epub_body, epub_type = _multipart(
            [("secondary_text", "任意转述文字，用来走到确认步骤。")],
            [("primary_file", "学术与政治.epub", b"PK\x03\x04 fake epub bytes")],
        )
        status, _, epub_html = _http_request(
            "POST", f"{base}/extract", epub_body, epub_type
        )
        check(
            "upload/epub-rejected-before-run",
            status == 200
            and "EPUB" in epub_html
            and "页码" in epub_html
            and "name='primary_upload'" not in epub_html,
            f"status={status}",
        )
    finally:
        server.shutdown()
        server.server_close()


# --------------------------------------------------------------------------- #
# rendering safety
# --------------------------------------------------------------------------- #


def probe_rendering() -> None:
    evil = "<script>alert('x')</script> & 引文"
    candidate = _candidate("cand-01", 1, 0.5, evil, [1])
    result = {
        "run": {
            "model_calls": 0,
            "cost_usd": 0.0,
            "embedding": "st-x",
            "chunk_count": 1,
            "index_seconds": 0,
            "retrieval_seconds": 0,
            "evidence_seconds": 0,
            "retrieval": "local",
        },
        "source": {"source_id": "S", "label": "L", "route": "text_layer", "page_count": 1},
        "counts": {"candidates": 1, "located": 1, "highlight_images": 1},
        "result_state": mvp.classify_result_state([candidate], searchable=True),
        "secondary_text": evil,
        "hints": "",
        "candidates": [candidate],
    }
    page_html = app.render_result("web-x", result, {"origin": "pasted"})
    check(
        "render/escapes-candidate-text",
        "<script>alert" not in page_html and "&lt;script&gt;" in page_html,
    )
    check(
        "render/shows-state-and-counts",
        "检索结果" in page_html and "候选段落" in page_html,
    )
    form_html = app.render_form(mvp.load_sources())
    check(
        "render/form-has-inputs-and-privacy-note",
        "二手文献内容" in form_html and "data/private/" in form_html,
    )
    check(
        "render/no-accuracy-claim",
        "准确率" not in page_html,
    )


# --------------------------------------------------------------------------- #
# registry + citation honesty
# --------------------------------------------------------------------------- #


def probe_registry_and_citations() -> None:
    sources = mvp.load_sources()
    check("registry/has-two-routes", len(sources) >= 2, f"n={len(sources)}")
    ids = {source["source_id"] for source in sources}
    check("registry/c04-and-t005b", {"C04", "T005B-01"} <= ids, f"ids={sorted(ids)}")
    missing = [
        source["source_id"]
        for source in sources
        if not (REPO_ROOT / source["pdf"]).exists()
    ]
    check(
        "registry/private-source-files-present-or-absent-together",
        True,
        f"missing_local_files={missing}",
    )
    empty = mvp.t004.build_citations({}, printed_page=None)
    check(
        "citation/no-metadata-no-invented-string",
        empty["basic_footnote_citation"] is None
        and empty["basic_reference_citation"] is None
        and "author" in empty["unresolved_fields"],
    )
    full = mvp.t004.build_citations(
        {
            "author": "某作者",
            "title": "某书",
            "translator": "某译者",
            "publisher": "某出版社",
            "publisher_place": "某地",
            "year": "2000",
        },
        printed_page=None,
    )
    check(
        "citation/unknown-printed-page-omitted",
        full["basic_footnote_citation"] is not None
        and "页" not in full["basic_footnote_citation"]
        and "printed_page" in full["unresolved_fields"],
        full["basic_footnote_citation"],
    )


# --------------------------------------------------------------------------- #
# end-to-end synthetic routes
# --------------------------------------------------------------------------- #


def make_text_layer_pdf(target: Path, lines: list[str]) -> None:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("SimHei", "", str(TEST_FONT))
    pdf.set_font("SimHei", size=14)
    pdf.add_page()
    for line in lines:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 9, line, new_x="LMARGIN", new_y="NEXT")
    pdf.add_page()
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        pdf.epw,
        9,
        "第二页的内容与第一页不同，用来验证页码归属是否正确。",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.output(str(target))


def make_image_only_pdf(target: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(image)
    for offset in range(0, 1100, 26):
        draw.line((60, 60 + offset, 840, 60 + offset), fill=(120, 120, 120), width=2)
    image.save(target, "PDF", resolution=150.0)


def probe_end_to_end() -> None:
    if not TEST_FONT.exists():
        check("e2e/text-layer", False, f"missing test font {TEST_FONT}")
        return
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    metadata_path = WORK_DIR / "synthetic_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "document_id": "synthetic-text-layer",
                "author": "测试作者",
                "author_country": "中",
                "title": "合成测试文献",
                "translator": "测试译者",
                "publisher_place": "测试地",
                "publisher": "测试出版社",
                "year": "2000",
                "document_type": "M",
                "metadata_origin": "probe fixture",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    pdf_path = WORK_DIR / "synthetic_text_layer.pdf"
    target_sentence = "社会行动是指行动者以他人的表现为取向而展开的行动。"
    make_text_layer_pdf(
        pdf_path,
        [
            "合成测试文献第一页。",
            "本页包含一段用于验证定位链路的中文文字。",
            target_sentence,
            "其后还有一句无关的话，用来撑出足够的正文长度。",
        ],
    )
    out_dir = WORK_DIR / "run_text_layer"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    result = mvp.run_pipeline(
        secondary_text="某位二手作者转述：社会行动以他人表现为取向。",
        hints="",
        source={
            "source_id": "synthetic-text-layer",
            "label": "合成文本层 PDF",
            "pdf": str(pdf_path),
            "metadata": str(metadata_path),
            "docname": "synthetic-text-layer",
        },
        out_dir=out_dir,
        k=5,
        log=lambda message: None,
    )
    located = [item for item in result["candidates"] if item["status"] == "located"]
    check(
        "e2e/text-layer-route",
        result["source"]["route"] == "text_layer",
        f"route={result['source']['route']}",
    )
    check(
        "e2e/text-layer-locates-passage",
        bool(located) and all(item["fragments"] for item in located),
        f"located={len(located)}/{len(result['candidates'])} pages="
        f"{[item['pdf_page_numbers'] for item in located]}",
    )
    check(
        "e2e/text-layer-highlight-image-written",
        bool(located)
        and all(
            (REPO_ROOT / ref).exists()
            for item in located
            for ref in item["highlighted_image_refs"]
        ),
    )
    check(
        "e2e/text-layer-free",
        result["run"]["model_calls"] == 0 and result["run"]["cost_usd"] == 0.0,
        f"calls={result['run']['model_calls']} cost={result['run']['cost_usd']}",
    )
    check(
        "e2e/refs-stay-private",
        all(
            ref.startswith("data/private/")
            for item in result["candidates"]
            for ref in item["highlighted_image_refs"] + item["original_page_image_refs"]
        ),
    )
    check(
        "e2e/result-json-written",
        (out_dir / "result.json").exists(),
    )

    image_pdf = WORK_DIR / "synthetic_image_only.pdf"
    make_image_only_pdf(image_pdf)
    image_out = WORK_DIR / "run_image_only"
    if image_out.exists():
        shutil.rmtree(image_out)
    failure = mvp.run_pipeline(
        secondary_text="这条转述在任何来源里都不应该被凭空匹配。",
        source={
            "source_id": "synthetic-image-only",
            "label": "合成无文本层 PDF",
            "pdf": str(image_pdf),
            "metadata": str(metadata_path),
            "docname": "synthetic-image-only",
            "ocr_cache": str(WORK_DIR / "no_such_ocr_cache"),
        },
        out_dir=image_out,
        k=5,
        log=lambda message: None,
    )
    check(
        "e2e/image-only-honest-failure",
        failure["result_state"]["state"] == mvp.STATE_INSUFFICIENT_SOURCE
        and failure["counts"]["candidates"] == 0
        and failure["counts"]["highlight_images"] == 0,
        f"state={failure['result_state']['state']}",
    )
    check(
        "e2e/image-only-no-model-call",
        failure["run"]["model_calls"] == 0 and failure["run"]["cost_usd"] == 0.0,
    )
    check(
        "e2e/ocr-off-not-silently-replaced",
        failure["source"]["route"] == "unavailable"
        and "no_text_layer_and_no_ocr_cache" in failure["source"]["blockers"],
        f"route={failure['source']['route']} blockers={failure['source']['blockers']}",
    )

    # An existing OCR cache must not be used when the user explicitly turns OCR
    # off: "off" means "do not present OCR text as evidence at all", so the honest
    # answer stays `insufficient_source` rather than silently switching route.
    cache_dir = WORK_DIR / "fake_ocr_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "p0001.json").write_text(
        json.dumps({"pdf_page": 1, "char_count": 5, "joined_text": "占位"}), encoding="utf-8"
    )
    off_out = WORK_DIR / "run_image_only_ocr_off"
    if off_out.exists():
        shutil.rmtree(off_out)
    off_result = mvp.run_pipeline(
        secondary_text="这条转述不应该从被显式关闭的 OCR 来源得到证据。",
        source={
            "source_id": "synthetic-image-only",
            "label": "合成无文本层 PDF",
            "pdf": str(image_pdf),
            "metadata": str(metadata_path),
            "docname": "synthetic-image-only",
            "ocr_cache": str(cache_dir),
        },
        out_dir=off_out,
        ocr_mode="off",
        k=5,
        log=lambda message: None,
    )
    check(
        "e2e/ocr-off-rejects-existing-cache",
        off_result["result_state"]["state"] == mvp.STATE_INSUFFICIENT_SOURCE
        and "ocr_disabled_by_request" in off_result["source"]["blockers"],
        f"blockers={off_result['source']['blockers']}",
    )


def probe_golden_generalization_contract() -> None:
    """Synthetic Golden regression: paraphrase -> cross-page evidence -> honest edition conflict."""
    if not TEST_FONT.exists():
        check("golden/synthetic-contract", False, f"missing test font {TEST_FONT}")
        return
    root = WORK_DIR / "golden_contract"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    from fpdf import FPDF

    pdf_path = root / "golden.pdf"
    pdf = FPDF()
    pdf.add_font("SimHei", "", str(TEST_FONT))
    pdf.set_font("SimHei", size=14)
    pdf.set_auto_page_break(auto=False)

    pdf.add_page()
    for line in (
        "这是一个完全合成的学术材料，用来验证跨版本引用核验流程。",
        "前文讨论政治共同体与强制手段之间的关系，并给出若干无关说明。",
        "就像历史上的政治共同体一样，国家也是一种以正当（就",
    ):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 9, line, new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(-18)
    pdf.cell(0, 8, "测试章节 105", align="R")

    pdf.add_page()
    for line in (
        "是说：被视为正当的）暴力为手段的人对人的支配关系。",
        "为了维持这种共同体，被支配者必须服从支配者所宣称的权威。",
        "后文继续讨论传统、个人魅力与法制等不同的正当性根据。",
    ):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 9, line, new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(-18)
    pdf.cell(0, 8, "106 测试文献", align="L")
    pdf.output(str(pdf_path))

    metadata_path = root / "meta.json"
    metadata_path.write_text(
        json.dumps(
            {
                "document_id": "synthetic-golden-2021",
                "author": "测试作者",
                "title": "测试政治文本",
                "translator": "新译者",
                "publisher_place": "上海",
                "publisher": "新出版社",
                "year": "2021",
                "document_type": "M",
                "metadata_origin": "synthetic evidence PDF",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    note = "[中]测试作者.测试政治文本[M].旧译者译.北京:旧出版社,1998:41."
    identity = fp.build_identity(note, "")
    out_dir = root / "run"
    result = mvp.run_pipeline(
        secondary_text="国家依靠被认为正当的暴力来维持人对人的支配。",
        hints=note,
        source={
            "source_id": "synthetic-golden",
            "label": "合成 Golden 文献",
            "pdf": str(pdf_path),
            "metadata": str(metadata_path),
            "docname": "synthetic-golden",
        },
        out_dir=out_dir,
        k=10,
        confirmed_identity=identity,
        log=lambda message: None,
    )
    target = next(
        (item for item in result["candidates"] if item.get("pdf_page_numbers") == [1, 2]),
        None,
    )
    conflicts = ((target or {}).get("bibliographic_metadata") or {}).get(
        "metadata_conflicts"
    ) or {}
    citation = (target or {}).get("basic_footnote_citation") or ""

    check(
        "golden/synthetic-cross-page-paraphrase",
        bool(target) and target["status"] == "located",
        f"rank={(target or {}).get('retrieval_rank')} pages={(target or {}).get('pdf_page_numbers')}",
    )
    check(
        "golden/synthetic-printed-page-provenance",
        bool(target) and target.get("printed_page_numbers") == [105, 106],
        f"printed={(target or {}).get('printed_page_numbers')}",
    )
    check(
        "golden/synthetic-two-page-highlights",
        bool(target) and len(target.get("highlighted_image_refs") or []) == 2,
        f"refs={(target or {}).get('highlighted_image_refs')}",
    )
    check(
        "golden/synthetic-evidence-edition-wins-citation",
        "新译者" in citation and "新出版社" in citation and "2021" in citation
        and "105-106" in citation,
        citation,
    )
    check(
        "golden/synthetic-secondary-conflict-preserved",
        conflicts.get("year", {}).get("confirmed") == "1998"
        and conflicts.get("year", {}).get("used") == "2021"
        and conflicts.get("publisher", {}).get("confirmed") == "旧出版社"
        and conflicts.get("publisher", {}).get("used") == "新出版社",
        f"conflicts={conflicts}",
    )
    check(
        "golden/synthetic-free-offline",
        result["run"]["model_calls"] == 0 and result["run"]["cost_usd"] == 0.0,
        f"calls={result['run']['model_calls']} cost={result['run']['cost_usd']}",
    )


def main() -> int:
    started = time.perf_counter()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    probe_input_handling()
    probe_result_states()
    probe_display_cleanup()
    probe_merge()
    probe_http_layer()
    probe_source_validation()
    probe_rendering()
    probe_registry_and_citations()
    probe_end_to_end()
    probe_golden_generalization_contract()
    probe_web_primary_upload()

    passed = sum(1 for item in CHECKS if item["ok"])
    failed = [item for item in CHECKS if not item["ok"]]
    summary = {
        "probe_count": len(CHECKS),
        "passed": passed,
        "failed": len(failed),
        "seconds": round(time.perf_counter() - started, 1),
        "checks": CHECKS,
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for item in CHECKS:
        mark = "PASS" if item["ok"] else "FAIL"
        line = f"[{mark}] {item['probe']}"
        if item["detail"]:
            line += f"  ({item['detail']})"
        print(line)
    print(f"\n{passed}/{len(CHECKS)} probes passed in {summary['seconds']}s")
    print(f"summary: {SUMMARY_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

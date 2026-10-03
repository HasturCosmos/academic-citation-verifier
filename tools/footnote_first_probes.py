#!/usr/bin/env python
"""Zero-cost probes for the footnote-first V0.2 workflow (D022 / D023).

These probes exercise the product simplification delivered under
``ops/FOOTNOTE_FIRST_SIMPLIFICATION_LONG_GOAL_2026-10-03.md``:

1. pasted quote + pasted footnote  -> deterministic author/title/page clues
2. quote/footnote screenshot       -> RapidOCR -> clues
3. footnote cites a standalone book
4. footnote cites an essay/chapter whose Chinese container is resolved separately
5. Chinese publication resolved but no accessible PDF -> upload request keeps identity
6. user already has the PDF        -> source search is never called
7. ambiguous/partial footnote      -> editable candidate confirmation
8. no useful footnote              -> ask for a better clue, never broad-search
9. provider failure                -> keep the bibliographic result, offer retry/upload
10. text-layer evidence path still works; image-only stays an honest failure

Everything here is deterministic, offline and free: no LLM call, no paid API,
no network. Any HTTP flow is served by the in-process ``mvp_app`` handler with
the paid/networked provider call monkeypatched. Synthetic PDFs/images live under
the git-ignored ``data/private/`` tree.

Run:

    .venv\\Scripts\\python.exe tools\\footnote_first_probes.py
"""

from __future__ import annotations

import html as html_lib
import json
import re
import shutil
import sys
import threading
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import footnote_parse as fp  # noqa: E402
import mvp_app as app  # noqa: E402
import mvp_pipeline as mvp  # noqa: E402
import source_acquisition as sa  # noqa: E402
from mvp_probes import (  # noqa: E402  (reuse the accepted probe fixtures)
    TEST_FONT,
    _http_request,
    _multipart,
    make_image_only_pdf,
    make_text_layer_pdf,
)

WORK_DIR = REPO_ROOT / "data/private/footnote_first_probes"
SUMMARY_PATH = WORK_DIR / "footnote_first_probe_summary.json"

CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append({"probe": name, "ok": bool(ok), "detail": detail})


# --------------------------------------------------------------------------- #
# 1-4: deterministic parsing and identity model
# --------------------------------------------------------------------------- #

WESTERN_ESSAY = (
    'Max Weber, "Objectivity in Social Science and Social Policy," in The '
    "Methodology of the Social Sciences, trans. Edward A. Shils and Henry A. "
    "Finch (Glencoe: Free Press, 1949), p. 50."
)
WESTERN_BOOK = "Max Weber, Economy and Society (Berkeley: University of California Press, 1978), 12."
CHINESE_BOOK = "马克斯·韦伯：《经济与社会》第一卷，阎克文译，上海人民出版社，2019年，第50页。"
CHINESE_ESSAY = "韦伯：《“客观性”》，载《社会科学方法论》，韩水法译，商务印书馆，2013年，第50页。"

# Pilot Case 001: the real GB/T-style footnote exactly as the user wrote it.
# The parser must read the note as written and must not "correct" the author or
# the publisher/page from outside knowledge (any catalog conflict is surfaced
# later as evidence, never baked into parsing).
CHINESE_GB_T_BOOK = "[德]马克思·韦伯.学术与政治[M].冯克利译.北京:外文出版社,1998:41."
CHINESE_GB_T_SHORT = "[德]马克斯·韦伯,学术与政治"
CHINESE_GB_T_FULLWIDTH = "［德］马克斯·韦伯，学术与政治[M]．冯克利译．北京：外文出版社，1998：41．"


def probe_parsing() -> None:
    western = fp.build_identity(WESTERN_ESSAY)
    work = western["cited_work"]
    check(
        "1.western-author-title-page",
        work["author"] == "Max Weber"
        and "Objectivity" in (work["title"] or "")
        and work["cited_page"] == "50",
        f"author={work['author']} title={work['title']} page={work['cited_page']}",
    )

    chinese = fp.build_identity(CHINESE_BOOK)
    zh_work = chinese["cited_work"]
    check(
        "1.chinese-author-title-page-translator",
        zh_work["author"] == "马克斯·韦伯"
        and zh_work["title"] == "经济与社会"
        and zh_work["cited_page"] == "50"
        and chinese["translator"] == "阎克文",
        f"work={zh_work} translator={chinese['translator']}",
    )


def probe_ocr_clues() -> None:
    if not TEST_FONT.exists():
        check("2.footnote-screenshot-ocr", False, f"missing font {TEST_FONT}")
        return
    from PIL import Image, ImageDraw, ImageFont

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    image_path = WORK_DIR / "footnote_fixture.png"
    image = Image.new("RGB", (1400, 220), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(TEST_FONT), 44)
    draw.text((30, 70), "马克斯·韦伯：《经济与社会》，第 50 页，2019 年。", fill="black", font=font)
    image.save(image_path)

    info = app.extract_secondary_text(upload_path=image_path, work_dir=WORK_DIR / "ocr")
    check(
        "2.footnote-screenshot-ocr",
        str(info.get("origin", "")).startswith("secondary_image_ocr")
        and int(info.get("text_chars") or 0) > 0,
        f"origin={info.get('origin')} chars={info.get('text_chars')}",
    )
    # The OCR text is fed straight into the same deterministic parser. The
    # fixture is large and clear, so at least one clue must survive.
    identity = fp.build_identity(info.get("text") or "")
    check(
        "2.ocr-text-yields-clues",
        fp.identity_is_useful(identity),
        f"title={identity['cited_work'].get('title')} page={identity['cited_work'].get('cited_page')}",
    )


def probe_cited_work_vs_container() -> None:
    standalone = fp.build_identity(WESTERN_BOOK)
    work = standalone["cited_work"]
    check(
        "3.standalone-book",
        work["work_type"] == "book"
        and work["title"] == "Economy and Society"
        and not standalone["containing_publications"]
        and "Max Weber Economy and Society" in fp.identity_queries(standalone),
        f"type={work['work_type']} containers={standalone['containing_publications']}",
    )

    essay = fp.build_identity(CHINESE_ESSAY)
    ework = essay["cited_work"]
    containers = essay["containing_publications"]
    check(
        "4.essay-and-container-are-distinct",
        ework["work_type"] == "essay"
        and ework["title"] == "客观性"
        and bool(containers)
        and containers[0]["title"] == "社会科学方法论"
        and containers[0]["title"] != ework["title"],
        f"work={ework['title']} container={containers[0]['title'] if containers else None}",
    )
    queries = fp.identity_queries(essay)
    check(
        "4b.lookup-prefers-confirmed-publication",
        bool(queries) and "社会科学方法论" in queries[0] and "韩水法" in queries[0],
        f"first_query={queries[0] if queries else None}",
    )


# --------------------------------------------------------------------------- #
# HTTP flows
# --------------------------------------------------------------------------- #


class Server:
    """An in-process product server with isolated git-ignored directories."""

    def __init__(self, name: str) -> None:
        root = WORK_DIR / name
        if root.exists():
            shutil.rmtree(root)
        self.runs = root / "runs"
        self.uploads = root / "uploads"
        self.finder = root / "finder"
        for directory in (self.runs, self.uploads, self.finder):
            directory.mkdir(parents=True, exist_ok=True)
        app.Handler.sources = mvp.load_sources()
        app.Handler.runs_dir = self.runs
        app.Handler.uploads_dir = self.uploads
        app.Handler.finder_dir = self.finder
        self.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        host, port = self.server.server_address
        self.base = f"http://{host}:{port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def post_form(base: str, path: str, data: dict) -> tuple[int, str]:
    body = urllib.parse.urlencode(data).encode("utf-8")
    status, _, html = _http_request(
        "POST", base + path, body, "application/x-www-form-urlencoded"
    )
    return status, html


def hidden_value(html_text: str, name: str) -> str:
    match = re.search(r"name='" + re.escape(name) + r"' value='([^']*)'", html_text)
    return html_lib.unescape(match.group(1)) if match else ""


def textarea_value(html_text: str, name: str) -> str:
    match = re.search(
        r"<textarea name='" + re.escape(name) + r"'[^>]*>(.*?)</textarea>",
        html_text,
        re.DOTALL,
    )
    return html_lib.unescape(match.group(1)) if match else ""


def probe_no_pdf_keeps_identity() -> None:
    server = Server("no_pdf")
    saved = sa.search_all
    payload = {
        "query": "韦伯 客观性",
        "providers": [{"provider": "openalex", "ok": True, "count": 0}],
        "outcome": {
            "status": sa.ACCESS_USER_UPLOAD,
            "message": "没有找到可直接使用的开放 PDF",
        },
        "results": [],
    }
    sa.search_all = lambda query, limit=6, **kwargs: payload
    try:
        status, identify_html = post_form(
            server.base, "/identify",
            {"secondary_text": "二手作者的转述文字。", "footnote": CHINESE_ESSAY},
        )
        check(
            "5.identify-shows-cited-work",
            status == 200 and "客观性" in identify_html and "社会科学方法论" in identify_html,
            f"status={status}",
        )
        status, find_html = post_form(
            server.base, "/find",
            {
                "secondary_text": "二手作者的转述文字。",
                "footnote": CHINESE_ESSAY,
                "id_author": "韦伯",
                "id_title": "客观性",
                "id_container_title": "社会科学方法论",
            },
        )
        check(
            "5.no-pdf-keeps-identity-and-asks-upload",
            status == 200
            and "当前没有找到可直接使用的 PDF" in find_html
            and "查找这一版" in find_html
            and "客观性" in find_html
            and "社会科学方法论" in find_html,
            f"status={status}",
        )
    finally:
        server.close()
        sa.search_all = saved


def probe_have_pdf_skips_search() -> None:
    if not TEST_FONT.exists():
        check("6.have-pdf-skips-search", False, f"missing font {TEST_FONT}")
        return
    server = Server("have_pdf")
    pdf_path = WORK_DIR / "synthetic_text_layer.pdf"
    make_text_layer_pdf(
        pdf_path,
        [
            "合成测试文献第一页。",
            "本页包含一段用于验证定位链路的中文文字。",
            "社会行动是指行动者以他人的表现为取向而展开的行动。",
            "其后还有一句无关的话，用来撑出足够的正文长度。",
        ],
    )
    called = {"value": False}
    saved = sa.search_all

    def forbidden(*args, **kwargs):
        called["value"] = True
        raise AssertionError("source search must not run when the user already has the PDF")

    sa.search_all = forbidden
    try:
        body, content_type = _multipart(
            [
                ("secondary_text", "某位二手作者转述：社会行动以他人表现为取向。"),
                ("footnote", "韦伯：《经济与社会》，第 12 页。"),
            ],
            [("primary_file", "synthetic-text-layer.pdf", pdf_path.read_bytes())],
        )
        status, _, confirm_html = _http_request("POST", server.base + "/extract", body, content_type)
        check(
            "6.have-pdf-reaches-confirm",
            status == 200 and "确认要检索的文本" in confirm_html,
            f"status={status}",
        )
        match = __import__("re").search(r"name='primary_upload' value='([^']*)'", confirm_html)
        uploaded = match.group(1) if match else ""
        run_fields = [
            ("secondary_text", "某位二手作者转述：社会行动以他人表现为取向。"),
            ("footnote", "韦伯：《经济与社会》，第 12 页。"),
            ("source", "C04"),
            ("primary_upload", uploaded),
            ("k", "5"),
            ("ocr_mode", "auto"),
        ]
        run_body, run_type = _multipart(run_fields)
        status, job_url, _ = _http_request("POST", server.base + "/run", run_body, run_type)
        job_id = job_url.rstrip("/").rsplit("/", 1)[-1] if "/job/" in job_url else ""
        finished = ""
        if job_id:
            deadline = time.time() + 180
            while time.time() < deadline:
                _, _, finished = _http_request("GET", f"{server.base}/job/{job_id}")
                if "查看结果" in finished or "运行失败" in finished:
                    break
                time.sleep(1.0)
        check(
            "6.have-pdf-runs-without-search",
            status == 200 and "查看结果" in finished and called["value"] is False,
            f"search_called={called['value']}",
        )
    finally:
        server.close()
        sa.search_all = saved


def probe_ambiguous_editable() -> None:
    server = Server("ambiguous")
    saved = sa.search_all
    sa.search_all = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("identify must not search providers")
    )
    try:
        status, html = post_form(
            server.base, "/identify",
            {"secondary_text": "二手转述。", "footnote": "马克斯·韦伯：《经济与社会》"},
        )
        check(
            "7.ambiguous-footnote-editable",
            status == 200
            and "核对或修改线索" in html
            and "name='id_author'" in html
            and "马克斯·韦伯" in html
            and "确认并按脚注查找" in html,
            f"status={status}",
        )
    finally:
        server.close()
        sa.search_all = saved


def probe_no_useful_footnote() -> None:
    server = Server("no_clue")
    called = {"value": False}
    saved = sa.search_all

    def forbidden(*args, **kwargs):
        called["value"] = True
        return {}

    sa.search_all = forbidden
    try:
        status, html = post_form(
            server.base, "/identify",
            {"secondary_text": "这一段转述没有给出任何可用脚注线索。", "footnote": ""},
        )
        check(
            "8.no-useful-footnote-asks",
            status == 200
            and "还需要一点脚注线索" in html
            and "不会退化成全网漫无目的的搜索" in html
            and called["value"] is False,
            f"status={status} search_called={called['value']}",
        )
    finally:
        server.close()
        sa.search_all = saved


def probe_provider_failure_preserves() -> None:
    server = Server("provider_down")
    saved = sa.search_all
    sa.search_all = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("all providers down"))
    try:
        status, html = post_form(
            server.base, "/find",
            {
                "secondary_text": "二手转述。",
                "footnote": "韦伯：《“客观性”》，载《社会科学方法论》，第50页。",
            },
        )
        check(
            "9.provider-failure-preserves-identity",
            status == 200
            and "查询开放来源时出错" in html
            and "客观性" in html
            and "重新查找" in html
            and "Traceback" not in html,
            f"status={status}",
        )
    finally:
        server.close()
        sa.search_all = saved


# --------------------------------------------------------------------------- #
# 10: evidence paths unchanged
# --------------------------------------------------------------------------- #


def probe_evidence_paths() -> None:
    if not TEST_FONT.exists():
        check("10.text-layer-evidence", False, f"missing font {TEST_FONT}")
        return
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    metadata_path = WORK_DIR / "synthetic_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "document_id": "footnote-first-synthetic",
                "author": "测试作者",
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
    make_text_layer_pdf(
        pdf_path,
        [
            "合成测试文献第一页。",
            "本页包含一段用于验证定位链路的中文文字。",
            "社会行动是指行动者以他人的表现为取向而展开的行动。",
            "其后还有一句无关的话，用来撑出足够的正文长度。",
        ],
    )
    out_dir = WORK_DIR / "run_text_layer"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    result = mvp.run_pipeline(
        secondary_text="某位二手作者转述：社会行动以他人表现为取向。",
        hints="韦伯：《经济与社会》，第12页。",  # footnote drives the hint pass
        source={
            "source_id": "footnote-first-synthetic",
            "label": "合成文本层 PDF",
            "pdf": str(pdf_path),
            "metadata": str(metadata_path),
            "docname": "footnote-first-synthetic",
        },
        out_dir=out_dir,
        k=5,
        log=lambda message: None,
    )
    located = [item for item in result["candidates"] if item["status"] == "located"]
    check(
        "10.text-layer-evidence",
        result["source"]["route"] == "text_layer"
        and bool(located)
        and result["run"]["model_calls"] == 0
        and all((REPO_ROOT / ref).exists() for item in located for ref in item["highlighted_image_refs"]),
        f"route={result['source']['route']} located={len(located)}",
    )

    image_pdf = WORK_DIR / "synthetic_image_only.pdf"
    make_image_only_pdf(image_pdf)
    failure = mvp.run_pipeline(
        secondary_text="这条转述不应该被凭空匹配。",
        hints="韦伯：《经济与社会》，第12页。",
        source={
            "source_id": "footnote-first-image-only",
            "label": "合成无文本层 PDF",
            "pdf": str(image_pdf),
            "metadata": str(metadata_path),
            "docname": "footnote-first-image-only",
            "ocr_cache": str(WORK_DIR / "no_such_ocr_cache"),
        },
        out_dir=WORK_DIR / "run_image_only",
        k=5,
        log=lambda message: None,
    )
    check(
        "10.image-only-still-honest-failure",
        failure["result_state"]["state"] == mvp.STATE_INSUFFICIENT_SOURCE
        and failure["counts"]["candidates"] == 0,
        f"state={failure['result_state']['state']}",
    )

    app_source = (TOOLS_DIR / "mvp_app.py").read_text(encoding="utf-8")
    check(
        "10.ocr-route-still-present",
        "RapidOCR 扫描识别（可选路径）" in app_source,
        "the adopted D017 OCR route must remain available",
    )


# --------------------------------------------------------------------------- #
# 11-18: acceptance-fix continuation probes (these fail on 9c929012)
# --------------------------------------------------------------------------- #

SECONDARY_SENTENCE = "某位二手作者转述：社会行动以他人表现为取向。"


def _ensure_text_pdf() -> Path:
    pdf_path = WORK_DIR / "synthetic_text_layer.pdf"
    if not pdf_path.exists():
        make_text_layer_pdf(
            pdf_path,
            [
                "合成测试文献第一页。",
                "本页包含一段用于验证定位链路的中文文字。",
                "社会行动是指行动者以他人的表现为取向而展开的行动。",
                "其后还有一句无关的话，用来撑出足够的正文长度。",
            ],
        )
    return pdf_path


def _make_image(path: Path, line: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1500, 220), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(TEST_FONT), 44)
    draw.text((30, 70), line, fill="black", font=font)
    image.save(path)


def _run_and_wait(server: "Server", fields: list, files: list | None = None) -> tuple[dict, str]:
    body, content_type = _multipart(fields, files)
    _, redirect, _ = _http_request("POST", server.base + "/run", body, content_type)
    job_id = redirect.rstrip("/").rsplit("/", 1)[-1] if "/job/" in redirect else ""
    finished = ""
    result: dict = {}
    if job_id:
        deadline = time.time() + 180
        while time.time() < deadline:
            _, _, finished = _http_request("GET", f"{server.base}/job/{job_id}")
            if "查看结果" in finished or "运行失败" in finished:
                break
            time.sleep(0.5)
        result_path = server.runs / job_id / "result.json"
        if result_path.exists():
            result = json.loads(result_path.read_text(encoding="utf-8"))
    return result, finished


EDITED_IDENTITY_FORM = {
    "secondary_text": SECONDARY_SENTENCE,
    "footnote": CHINESE_ESSAY,
    "id_author": "韦伯",
    "id_title": "客观性",
    "id_container_title": "社会科学方法论",
    "id_translator": "韩水法",
    "id_publisher": "商务印书馆",
    "id_year": "2013",
}


def probe_identify_ingests_uploads() -> None:
    """P0-A: /identify must consume the secondary screenshot/PDF, not drop it."""
    if not TEST_FONT.exists():
        check("11.identify-reads-secondary-upload", False, f"missing font {TEST_FONT}")
        check("11.identify-reads-footnote-upload", False, f"missing font {TEST_FONT}")
        return
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    server = Server("identify_uploads")
    called = {"value": False}
    saved = sa.search_all
    sa.search_all = lambda *a, **k: (called.__setitem__("value", True), {})[1]
    try:
        secondary_img = WORK_DIR / "identify_secondary.png"
        note_img = WORK_DIR / "identify_note.png"
        _make_image(
            secondary_img,
            "二手作者转述：社会行动是指行动者以他人的表现为取向而展开的行动。",
        )
        _make_image(note_img, "马克斯·韦伯：《经济与社会》，第 50 页，2019 年。")
        body, content_type = _multipart(
            [],
            [
                ("secondary_file", "secondary.png", secondary_img.read_bytes()),
                ("footnote_file", "footnote.png", note_img.read_bytes()),
            ],
        )
        status, _, page_html = _http_request(
            "POST", server.base + "/identify", body, content_type
        )
        carried = hidden_value(page_html, "secondary_text")
        check(
            "11.identify-reads-secondary-upload",
            status == 200
            and len(carried) >= 10
            and any("\u4e00" <= char <= "\u9fff" for char in carried),
            f"status={status} carried_chars={len(carried)}",
        )
        check(
            "11.identify-reads-footnote-upload",
            status == 200 and "经济与社会" in page_html and called["value"] is False,
            f"status={status} search_called={called['value']}",
        )
    finally:
        server.close()
        sa.search_all = saved


def probe_extract_ingests_footnote_screenshot() -> None:
    """P0-B: the owned-PDF path must read a footnote screenshot and skip search."""
    if not TEST_FONT.exists():
        check("12.extract-reads-footnote-screenshot", False, f"missing font {TEST_FONT}")
        check("12.owned-pdf-run-keeps-note-no-search", False, f"missing font {TEST_FONT}")
        return
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    server = Server("extract_note")
    pdf_path = _ensure_text_pdf()
    note_img = WORK_DIR / "extract_note.png"
    _make_image(note_img, "马克斯·韦伯：《经济与社会》，第 50 页，2019 年。")
    called = {"value": False}
    saved = sa.search_all

    def forbidden(*args, **kwargs):
        called["value"] = True
        raise AssertionError("owned-PDF path must not run source search")

    sa.search_all = forbidden
    try:
        body, content_type = _multipart(
            [("secondary_text", SECONDARY_SENTENCE)],
            [
                ("footnote_file", "note.png", note_img.read_bytes()),
                ("primary_file", "syn.pdf", pdf_path.read_bytes()),
            ],
        )
        status, _, confirm = _http_request(
            "POST", server.base + "/extract", body, content_type
        )
        note_in_confirm = textarea_value(confirm, "footnote")
        check(
            "12.extract-reads-footnote-screenshot",
            status == 200 and len(note_in_confirm) >= 8 and "经济" in note_in_confirm,
            f"status={status} note_chars={len(note_in_confirm)}",
        )
        uploaded = hidden_value(confirm, "primary_upload")
        result, finished = _run_and_wait(
            server,
            [
                ("secondary_text", SECONDARY_SENTENCE),
                ("footnote", note_in_confirm),
                ("primary_upload", uploaded),
                ("k", "5"),
                ("ocr_mode", "auto"),
            ],
        )
        check(
            "12.owned-pdf-run-keeps-note-no-search",
            bool(result)
            and bool(result.get("hints"))
            and result.get("counts", {}).get("candidates", 0) > 0
            and called["value"] is False,
            f"hints={bool(result.get('hints'))} search_called={called['value']}",
        )
    finally:
        server.close()
        sa.search_all = saved


def probe_find_no_pdf_continuation_keeps_identity() -> None:
    """P0-C: edited identity survives /find -> no PDF -> owned-PDF upload -> run."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    server = Server("no_pdf_identity")
    pdf_path = _ensure_text_pdf()
    saved = sa.search_all
    sa.search_all = lambda *a, **k: {
        "query": "社会科学方法论 韩水法",
        "providers": [{"provider": "openalex", "ok": True, "count": 0}],
        "outcome": {
            "status": sa.ACCESS_USER_UPLOAD,
            "message": "没有找到可直接使用的开放 PDF",
        },
        "results": [],
    }
    try:
        status, find_html = post_form(server.base, "/find", dict(EDITED_IDENTITY_FORM))
        carried_identity = hidden_value(find_html, "identity_json")
        check(
            "13.find-no-pdf-carries-identity",
            status == 200
            and bool(carried_identity)
            and "社会科学方法论" in carried_identity
            and "当前没有找到可直接使用的 PDF" in find_html,
            f"status={status} carried={bool(carried_identity)}",
        )
        body, content_type = _multipart(
            [
                ("secondary_text", SECONDARY_SENTENCE),
                ("footnote", CHINESE_ESSAY),
                ("identity_json", carried_identity),
            ],
            [("primary_file", "syn.pdf", pdf_path.read_bytes())],
        )
        _, _, confirm = _http_request(
            "POST", server.base + "/extract", body, content_type
        )
        uploaded = hidden_value(confirm, "primary_upload")
        identity_hidden = hidden_value(confirm, "identity_json")
        result, _ = _run_and_wait(
            server,
            [
                ("secondary_text", SECONDARY_SENTENCE),
                ("footnote", CHINESE_ESSAY),
                ("primary_upload", uploaded),
                ("identity_json", identity_hidden),
                ("k", "5"),
                ("ocr_mode", "auto"),
            ],
        )
        meta = ((result.get("candidates") or [{}])[0]).get("bibliographic_metadata") or {}
        check(
            "13.owned-pdf-continuation-keeps-edited-identity",
            bool(result)
            and meta.get("author") == "韦伯"
            and meta.get("title") == "社会科学方法论"
            and meta.get("translator") == "韩水法"
            and meta.get("year") == "2013",
            f"author={meta.get('author')} title={meta.get('title')} "
            f"translator={meta.get('translator')}",
        )
    finally:
        server.close()
        sa.search_all = saved


def probe_use_found_keeps_identity_and_citation() -> None:
    """P0-C + P1-E: edited identity survives /use_found and feeds an honest citation."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    server = Server("use_found_identity")
    pdf_path = _ensure_text_pdf()
    saved_search = sa.search_all
    saved_download = sa.download_open_pdf
    record = {
        "title": "社会科学方法论",
        "authors": ["韦伯"],
        "year": "2013",
        "access_status": sa.ACCESS_OPEN_PDF,
        "evidence_eligible": True,
        "source_provider": "openalex",
        "license": "CC BY",
        "landing_url": "https://example.invalid/work",
        "pdf_url": "https://example.invalid/work.pdf",
        "match_score": 1.0,
    }
    sa.search_all = lambda *a, **k: {
        "query": "社会科学方法论 韩水法",
        "providers": [{"provider": "openalex", "ok": True, "count": 1}],
        "outcome": {"status": sa.ACCESS_OPEN_PDF, "message": "找到可直接下载的开放 PDF"},
        "results": [record],
    }

    def fake_download(rec, dest_dir, **kwargs):
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / "downloaded.pdf"
        target.write_bytes(pdf_path.read_bytes())
        return {
            "path": str(target),
            "bytes": target.stat().st_size,
            "sha256": "0" * 64,
            "source_provider": rec.get("source_provider"),
            "landing_url": rec.get("landing_url"),
            "pdf_url": rec.get("pdf_url"),
            "license": rec.get("license"),
            "title": rec.get("title"),
            "authors": rec.get("authors"),
            "year": rec.get("year"),
            "identifiers": rec.get("identifiers"),
        }

    sa.download_open_pdf = fake_download
    try:
        status, find_html = post_form(server.base, "/find", dict(EDITED_IDENTITY_FORM))
        token = hidden_value(find_html, "token")
        index = hidden_value(find_html, "index") or "0"
        identity_hidden = hidden_value(find_html, "identity_json")
        check(
            "14.find-open-pdf-carries-identity",
            status == 200 and "下载这个开放 PDF" in find_html and bool(token)
            and bool(identity_hidden),
            f"status={status} token={bool(token)}",
        )
        _, confirm = post_form(
            server.base,
            "/use_found",
            {
                "token": token,
                "index": index,
                "secondary_text": SECONDARY_SENTENCE,
                "footnote": CHINESE_ESSAY,
                "hints": "",
                "identity_json": identity_hidden,
            },
        )
        uploaded = hidden_value(confirm, "primary_upload")
        identity_hidden2 = hidden_value(confirm, "identity_json")
        result, _ = _run_and_wait(
            server,
            [
                ("secondary_text", SECONDARY_SENTENCE),
                ("footnote", CHINESE_ESSAY),
                ("primary_upload", uploaded),
                ("identity_json", identity_hidden2),
                ("k", "5"),
                ("ocr_mode", "auto"),
            ],
        )
        candidate = (result.get("candidates") or [{}])[0]
        meta = candidate.get("bibliographic_metadata") or {}
        check(
            "14.use-found-run-keeps-edited-identity",
            bool(result)
            and meta.get("author") == "韦伯"
            and meta.get("title") == "社会科学方法论"
            and meta.get("translator") == "韩水法",
            f"author={meta.get('author')} title={meta.get('title')}",
        )
        provenance = meta.get("metadata_provenance") or {}
        citation = candidate.get("basic_footnote_citation") or ""
        check(
            "15.confirmed-fields-produce-honest-citation",
            bool(citation)
            and "社会科学方法论" in citation
            and "韩水法" in citation
            and "2013" in citation
            and bool(provenance.get("title")),
            f"citation={citation!r} provenance_title={provenance.get('title')!r}",
        )
    finally:
        server.close()
        sa.search_all = saved_search
        sa.download_open_pdf = saved_download


def probe_foreign_note_no_chinese_citation() -> None:
    """A foreign note with no Chinese-edition metadata must not fake a Chinese citation."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = _ensure_text_pdf()
    out_dir = WORK_DIR / "run_foreign_identity"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    result = mvp.run_pipeline(
        secondary_text=SECONDARY_SENTENCE,
        hints=WESTERN_ESSAY,
        source={
            "source_id": "foreign-synthetic",
            "label": "合成无元数据 PDF",
            "pdf": str(pdf_path),
            "metadata": "",
            "docname": "foreign-synthetic",
        },
        out_dir=out_dir,
        k=5,
        confirmed_identity=fp.build_identity(WESTERN_ESSAY),
        log=lambda message: None,
    )
    candidates = result.get("candidates") or []
    citations = [item.get("basic_footnote_citation") for item in candidates]
    confirmed_flags = [
        (item.get("bibliographic_metadata") or {}).get("chinese_edition_confirmed")
        for item in candidates
    ]
    check(
        "16.foreign-note-no-fabricated-chinese-citation",
        bool(candidates)
        and all(citation is None for citation in citations)
        and all(flag is False for flag in confirmed_flags),
        f"citations={citations}",
    )


def probe_need_more_clue_is_editable() -> None:
    """P1-D: the "need more clue" page must let the user actually add a clue."""
    server = Server("need_clue")
    saved = sa.search_all
    sa.search_all = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("identify must not search providers")
    )
    try:
        status, page_html = post_form(
            server.base,
            "/identify",
            {"secondary_text": "这一段转述没有给出任何可用脚注线索。", "footnote": ""},
        )
        check(
            "17.need-more-clue-editable",
            status == 200
            and "还需要一点脚注线索" in page_html
            and "<textarea name='footnote'" in page_html
            and "name='footnote_file'" in page_html
            and "name='primary_file'" in page_html,
            f"status={status}",
        )
        status2, page2 = post_form(
            server.base,
            "/identify",
            {"secondary_text": "这一段转述没有给出任何可用脚注线索。", "footnote": CHINESE_BOOK},
        )
        check(
            "17.need-more-clue-retry-accepts-new-clue",
            status2 == 200 and "经济与社会" in page2 and "核对或修改线索" in page2,
            f"status={status2}",
        )
    finally:
        server.close()
        sa.search_all = saved


def probe_gbt_footnote_intake() -> None:
    """Pilot Case 001: common Chinese GB/T-style footnotes must be recognized.

    Every one of these fails on the accepted baseline ``ecbd2c9``: the old parser
    expected ``作者《…》`` and returned "还需要一点脚注线索" for the real note.
    """
    parsed = fp.build_identity(CHINESE_GB_T_BOOK)
    work = parsed["cited_work"]
    check(
        "23.gbt-note-author-title-translator-publisher-page",
        work["author"] == "马克思·韦伯"
        and work["title"] == "学术与政治"
        and parsed["translator"] == "冯克利"
        and parsed["publisher"] == "外文出版社"
        and work["year"] == "1998"
        and work["cited_page"] == "41"
        and fp.identity_is_useful(parsed),
        f"author={work['author']} title={work['title']} translator={parsed['translator']} "
        f"publisher={parsed['publisher']} year={work['year']} page={work['cited_page']}",
    )
    check(
        "23b.gbt-note-faithful-not-corrected",
        # The nationality prefix must not leak into the author, and the parser
        # keeps the note's own publisher/page even though catalogs may differ.
        work["author"] == "马克思·韦伯"
        and "德" not in (work["author"] or "")
        and "[" not in (work["author"] or "")
        and parsed["publisher"] == "外文出版社"
        and work["cited_page"] == "41",
        f"author={work['author']!r} publisher={parsed['publisher']!r}",
    )

    short = fp.build_identity(CHINESE_GB_T_SHORT)
    short_work = short["cited_work"]
    check(
        "24.gbt-short-clue-author-title",
        short_work["author"] == "马克斯·韦伯"
        and short_work["title"] == "学术与政治"
        and fp.identity_is_useful(short)
        and "马克斯·韦伯 学术与政治" in fp.identity_queries(short),
        f"author={short_work['author']} title={short_work['title']} "
        f"queries={fp.identity_queries(short)}",
    )

    full = fp.build_identity(CHINESE_GB_T_FULLWIDTH)
    full_work = full["cited_work"]
    check(
        "24b.gbt-mixed-punctuation",
        full_work["author"] == "马克斯·韦伯"
        and full_work["title"] == "学术与政治"
        and full["translator"] == "冯克利"
        and full["publisher"] == "外文出版社"
        and full_work["year"] == "1998"
        and full_work["cited_page"] == "41",
        f"fields={full_work} translator={full['translator']} publisher={full['publisher']}",
    )

    # No regression: the legacy 《…》 / quoted Chinese and Western shapes still parse.
    legacy_book = fp.build_identity(CHINESE_BOOK)["cited_work"]
    legacy_essay = fp.build_identity(CHINESE_ESSAY)
    western = fp.build_identity(WESTERN_ESSAY)["cited_work"]
    check(
        "24c.legacy-parsing-not-regressed",
        legacy_book["title"] == "经济与社会"
        and legacy_book["author"] == "马克斯·韦伯"
        and legacy_essay["cited_work"]["title"] == "客观性"
        and bool(legacy_essay["containing_publications"])
        and legacy_essay["containing_publications"][0]["title"] == "社会科学方法论"
        and western["author"] == "Max Weber"
        and "Objectivity" in (western["title"] or ""),
        f"book={legacy_book['title']} essay={legacy_essay['cited_work']['title']} "
        f"western={western['title']}",
    )


def probe_gbt_retry_visible_feedback() -> None:
    """P1-J: an insufficient retry must visibly say what is still missing."""
    server = Server("gbt_retry")
    called = {"value": False}
    saved = sa.search_all

    def forbidden(*args, **kwargs):
        called["value"] = True
        return {}

    sa.search_all = forbidden
    try:
        status, page_html = post_form(
            server.base,
            "/identify",
            {"secondary_text": "二手转述。", "footnote": "同上。"},
        )
        check(
            "25.insufficient-retry-visible-message",
            status == 200
            and "还需要一点脚注线索" in page_html
            and "仍然没能从这段脚注里读出可用的书目线索" in page_html
            and "篇名/书名" in page_html
            and "同上" in textarea_value(page_html, "footnote")
            and called["value"] is False,
            f"status={status} search_called={called['value']}",
        )

        status2, page2 = post_form(
            server.base,
            "/identify",
            {"secondary_text": "二手转述。", "footnote": CHINESE_GB_T_BOOK},
        )
        check(
            "25b.gbt-note-reaches-identity-screen",
            status2 == 200
            and "核对或修改线索" in page2
            and "学术与政治" in page2
            and "马克思·韦伯" in page2
            and "还需要一点脚注线索" not in page2,
            f"status={status2}",
        )

        status3, page3 = post_form(
            server.base,
            "/identify",
            {"secondary_text": "这一段没有脚注。", "footnote": ""},
        )
        check(
            "25c.initial-clue-page-stays-distinct-from-retry",
            status3 == 200
            and "还需要一点脚注线索" in page3
            and "仍然没能从这段脚注里读出可用的书目线索" not in page3,
            f"status={status3}",
        )
    finally:
        server.close()
        sa.search_all = saved


def probe_source_resolution_safety() -> None:
    """P0-K / P0-L / P1-M: weak records must not be actionable in normal UX.

    Pilot Case 001 second finding: after the GB/T note was accepted, the finder
    correctly labelled the matches as weak, yet still rendered unrelated
    OpenAlex open PDFs with a prominent "download and verify" button, and the
    search query leaned on the note's unverified author string.
    """
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    server = Server("source_resolution_safety")
    captured: dict = {"query": None}
    saved_search = sa.search_all
    saved_download = sa.download_open_pdf

    unrelated = sa._record(
        source_provider="openalex",
        title="政治学与学术研究方法论",
        authors=["李四"],
        year="2015",
        access_status=sa.ACCESS_OPEN_PDF,
        pdf_url="https://example.org/unrelated.pdf",
        license="CC BY",
        landing_url="https://example.org/unrelated",
        match_score=0.75,
    )
    anchored = sa._record(
        source_provider="google_books",
        title="学术与政治",
        authors=["马克斯·韦伯"],
        year="1998",
        access_status=sa.ACCESS_OPEN_PDF,
        pdf_url="https://example.org/weber.pdf",
        license="public domain",
        landing_url="https://example.org/weber",
        match_score=0.625,
    )
    payload_records: list[dict] = []

    def fake_search(query, **kwargs):
        captured["query"] = query
        return {
            "query": query,
            "providers": [{"provider": "openalex", "ok": True, "count": len(payload_records)}],
            "outcome": {
                "status": sa.ACCESS_USER_UPLOAD,
                "message": "只找到与查询弱相关的记录，没有可用作页码可核验证据的开放 PDF。",
            },
            "results": list(payload_records),
        }

    def forbidden_download(*args, **kwargs):
        raise AssertionError("an unrelated record must never be downloaded")

    sa.search_all = fake_search
    sa.download_open_pdf = forbidden_download
    try:
        # 1. Only an unrelated, downloadable record comes back.
        payload_records[:] = [unrelated]
        status, weak_html = post_form(
            server.base,
            "/find",
            {"secondary_text": SECONDARY_SENTENCE, "footnote": CHINESE_GB_T_BOOK},
        )
        check(
            "27.query-prefers-stable-edition-clues",
            status == 200 and captured["query"] == "学术与政治 冯克利 1998",
            f"status={status} query={captured['query']!r}",
        )
        check(
            "27.weak-record-not-actionable",
            "action='/use_found'" not in weak_html
            and "下载这个开放 PDF" not in weak_html,
            "an unrelated downloadable PDF must not render a download/use action",
        )
        check(
            "27.honest-empty-state",
            "当前没有找到可直接使用的 PDF" in weak_html
            and "可信匹配" in weak_html
            and "不相关" in weak_html,
            "the page must plainly say no trustworthy matching candidate was found",
        )
        check(
            "27.weak-record-moved-to-debug",
            "开发者 / 调试：本次未采用的记录" in weak_html
            and "政治学与学术研究方法论" in weak_html,
            "the record may stay visible only as collapsed debug detail",
        )
        check(
            "27.upload-and-bundle-fallback-intact",
            "name='primary_file'" in weak_html
            and "action='/extract'" in weak_html
            and "查找这一版" in weak_html,
            "the owned-PDF upload and the copyable edition bundle must survive",
        )

        # 2. An anchored record stays actionable; the unrelated one stays hidden.
        payload_records[:] = [anchored, unrelated]
        status, good_html = post_form(
            server.base,
            "/find",
            {"secondary_text": SECONDARY_SENTENCE, "footnote": CHINESE_GB_T_BOOK},
        )
        check(
            "27.anchored-record-remains-actionable",
            status == 200
            and "下载这个开放 PDF" in good_html
            and good_html.count("action='/use_found'") == 1,
            f"status={status} use_found_forms={good_html.count(chr(39) + '/use_found' + chr(39))}",
        )
        check(
            "27.unrelated-still-hidden-next-to-a-good-match",
            "开发者 / 调试：本次未采用的记录" in good_html
            and "政治学与学术研究方法论" in good_html,
            "relevance gating is per record, not per query",
        )

        # 3. Server-side defence: posting the weak record's index is refused.
        status, refused = post_form(
            server.base,
            "/use_found",
            {
                "token": hidden_value(good_html, "token"),
                "index": "1",
                "secondary_text": SECONDARY_SENTENCE,
                "footnote": CHINESE_GB_T_BOOK,
                "hints": "",
                "identity_json": hidden_value(good_html, "identity_json"),
            },
        )
        check(
            "27.use-found-refuses-weak-record",
            status == 200 and "这条记录不能自动下载" in refused,
            f"status={status} has_message={'这条记录不能自动下载' in refused}",
        )
    finally:
        server.close()
        sa.search_all = saved_search
        sa.download_open_pdf = saved_download

    # 4. Query planning and the anchor never mutate the parsed identity (P0-L).
    identity = fp.build_identity(CHINESE_GB_T_BOOK)
    queries = fp.identity_queries(identity)
    work = identity["cited_work"]
    check(
        "27.identity-not-mutated-by-query-planning",
        work["author"] == "马克思·韦伯"
        and work["title"] == "学术与政治"
        and identity["translator"] == "冯克利"
        and identity["publisher"] == "外文出版社"
        and work["year"] == "1998"
        and work["cited_page"] == "41",
        f"author={work['author']!r} publisher={identity['publisher']!r}",
    )
    check(
        "27.queries-keep-author-form-as-fallback",
        bool(queries)
        and queries[0] == "学术与政治 冯克利 1998"
        and "马克思·韦伯 学术与政治" in queries,
        f"queries={queries}",
    )
    check(
        "27.anchor-uses-confirmed-title",
        fp.identity_anchor(identity)["titles"] == ["学术与政治"],
        str(fp.identity_anchor(identity)),
    )


def probe_gbt_parser_stays_offline() -> None:
    """Probe 6: the extended parser adds no network, model or dependency."""
    source = (TOOLS_DIR / "footnote_parse.py").read_text(encoding="utf-8")
    banned = (
        "import requests", "import urllib", "import urllib3", "import http",
        "import socket", "import openai", "import litellm", "from openai",
        "from requests", "http.client", "urlopen", "requests.",
    )
    hits = [token for token in banned if token in source]
    check(
        "26.gbt-parser-still-offline-stdlib",
        not hits and "import re" in source,
        f"banned_hits={hits}",
    )


def probe_network_and_evidence_invariant() -> None:
    """The bounded network architecture and the accepted evidence routes are intact."""
    app_source = (TOOLS_DIR / "mvp_app.py").read_text(encoding="utf-8")
    pipeline_source = (TOOLS_DIR / "mvp_pipeline.py").read_text(encoding="utf-8")
    check(
        "18.single-targeted-network-call",
        app_source.count("sa.search_all(") == 1
        and "import source_acquisition" not in pipeline_source,
        f"search_all_calls={app_source.count('sa.search_all(')}",
    )
    check(
        "18.evidence-routes-intact",
        "RapidOCR 扫描识别（可选路径）" in app_source
        and "PDF 文本层（默认路径）" in app_source,
        "text-layer + RapidOCR evidence routes remain in the product surface",
    )


def probe_no_pdf_page_renders_real_upload() -> None:
    """P0-F: the no-PDF page must expose a usable owned-PDF upload in the browser."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    server = Server("no_pdf_upload")
    pdf_path = _ensure_text_pdf()
    calls = {"n": 0}
    saved = sa.search_all

    def fake_search(query, **kwargs):
        calls["n"] += 1
        return {
            "query": query,
            "providers": [{"provider": "openalex", "ok": True, "count": 0}],
            "outcome": {
                "status": sa.ACCESS_USER_UPLOAD,
                "message": "没有找到可直接使用的开放 PDF",
            },
            "results": [],
        }

    sa.search_all = fake_search
    try:
        status, find_html = post_form(server.base, "/find", dict(EDITED_IDENTITY_FORM))
        has_upload = (
            "name='primary_file'" in find_html
            and "enctype='multipart/form-data'" in find_html
            and "action='/extract'" in find_html
        )
        check(
            "19.no-pdf-page-renders-pdf-upload",
            status == 200 and has_upload,
            f"status={status} has_upload={has_upload}",
        )
        # Submit exactly what the rendered browser form would submit.
        rendered = [
            ("secondary_text", hidden_value(find_html, "secondary_text")),
            ("footnote", hidden_value(find_html, "footnote")),
            ("hints", hidden_value(find_html, "hints")),
            ("identity_json", hidden_value(find_html, "identity_json")),
        ]
        body, content_type = _multipart(
            rendered, [("primary_file", "syn.pdf", pdf_path.read_bytes())]
        )
        _, _, confirm = _http_request(
            "POST", server.base + "/extract", body, content_type
        )
        uploaded = hidden_value(confirm, "primary_upload")
        identity_hidden = hidden_value(confirm, "identity_json")
        result, _ = _run_and_wait(
            server,
            [
                ("secondary_text", hidden_value(find_html, "secondary_text")),
                ("footnote", hidden_value(find_html, "footnote")),
                ("primary_upload", uploaded),
                ("identity_json", identity_hidden),
                ("k", "5"),
                ("ocr_mode", "auto"),
            ],
        )
        meta = ((result.get("candidates") or [{}])[0]).get("bibliographic_metadata") or {}
        check(
            "19.rendered-upload-reaches-run-without-search",
            bool(result)
            and meta.get("author") == "韦伯"
            and meta.get("title") == "社会科学方法论"
            and calls["n"] == 1,
            f"search_calls={calls['n']} author={meta.get('author')} title={meta.get('title')}",
        )
    finally:
        server.close()
        sa.search_all = saved


def probe_cleared_identity_field_stays_clear() -> None:
    """P0-G: intentionally blanking a parsed field must clear it, not reparse it."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    server = Server("cleared_field")
    captured = {"query": None}
    saved = sa.search_all

    def fake_search(query, **kwargs):
        captured["query"] = query
        return {
            "query": query,
            "providers": [{"provider": "openalex", "ok": True, "count": 0}],
            "outcome": {
                "status": sa.ACCESS_USER_UPLOAD,
                "message": "没有找到可直接使用的开放 PDF",
            },
            "results": [],
        }

    sa.search_all = fake_search
    try:
        # CHINESE_BOOK parses author=马克斯·韦伯; the user clears it on the form.
        status, find_html = post_form(
            server.base,
            "/find",
            {
                "secondary_text": "二手转述。",
                "footnote": CHINESE_BOOK,
                "id_author": "",
                "id_title": "经济与社会",
                "id_translator": "阎克文",
                "id_publisher": "上海人民出版社",
                "id_year": "2019",
            },
        )
        try:
            echoed = json.loads(hidden_value(find_html, "identity_json") or "{}")
        except json.JSONDecodeError:
            echoed = {}
        echoed_work = echoed.get("cited_work") or {}
        query = captured["query"] or ""
        check(
            "20.cleared-field-not-reparsed",
            status == 200
            and bool(query)
            and "马克斯" not in query
            and "韦伯" not in query
            and not echoed_work.get("author"),
            f"query={query!r} echoed_author={echoed_work.get('author')!r}",
        )
        # And the cleared field must not sneak back through the citation composer.
        ident = fp.build_identity(CHINESE_BOOK, overrides={"author": ""})
        meta = fp.compose_citation_metadata({}, ident)
        citation = mvp.t004.build_citations(meta)["basic_footnote_citation"]
        check(
            "20.cleared-field-respected-downstream",
            meta.get("author") in (None, "") and citation is None,
            f"author={meta.get('author')!r} citation={citation!r}",
        )
    finally:
        server.close()
        sa.search_all = saved


def probe_direct_upload_from_identity_screen_keeps_edits() -> None:
    """P0-H: edits made on the identity screen must survive the direct upload route."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    server = Server("identity_direct_upload")
    pdf_path = _ensure_text_pdf()
    called = {"value": False}
    saved = sa.search_all

    def forbidden(*args, **kwargs):
        called["value"] = True
        raise AssertionError("the direct owned-PDF route must not call source search")

    sa.search_all = forbidden
    try:
        status, identity_html = post_form(
            server.base,
            "/identify",
            {"secondary_text": SECONDARY_SENTENCE, "footnote": CHINESE_BOOK},
        )
        check(
            "21.identity-screen-in-form-upload",
            status == 200
            and "formaction='/extract'" in identity_html
            and "enctype='multipart/form-data'" in identity_html
            and "name='primary_file'" in identity_html,
            f"status={status}",
        )
        # The user edits the parsed fields and clicks the in-form upload button.
        edited = {
            "secondary_text": SECONDARY_SENTENCE,
            "footnote": CHINESE_BOOK,
            "id_author": "韦伯",
            "id_title": "社会科学方法论",
            "id_container_title": "社会科学方法论",
            "id_translator": "韩水法",
            "id_publisher": "商务印书馆",
            "id_year": "2013",
        }
        body, content_type = _multipart(
            list(edited.items()), [("primary_file", "syn.pdf", pdf_path.read_bytes())]
        )
        _, _, confirm = _http_request(
            "POST", server.base + "/extract", body, content_type
        )
        uploaded = hidden_value(confirm, "primary_upload")
        identity_hidden = hidden_value(confirm, "identity_json")
        result, _ = _run_and_wait(
            server,
            [
                ("secondary_text", SECONDARY_SENTENCE),
                ("footnote", CHINESE_BOOK),
                ("primary_upload", uploaded),
                ("identity_json", identity_hidden),
                ("k", "5"),
                ("ocr_mode", "auto"),
            ],
        )
        candidate = (result.get("candidates") or [{}])[0]
        meta = candidate.get("bibliographic_metadata") or {}
        citation = candidate.get("basic_footnote_citation") or ""
        check(
            "21.direct-upload-keeps-edited-identity",
            bool(result)
            and meta.get("author") == "韦伯"
            and meta.get("title") == "社会科学方法论"
            and meta.get("translator") == "韩水法"
            and called["value"] is False,
            f"author={meta.get('author')!r} title={meta.get('title')!r} "
            f"translator={meta.get('translator')!r} search_called={called['value']}",
        )
        check(
            "21.direct-upload-citation-uses-edits",
            "社会科学方法论" in citation and "韩水法" in citation,
            f"citation={citation!r}",
        )
    finally:
        server.close()
        sa.search_all = saved


def main() -> int:
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    probe_parsing()
    probe_ocr_clues()
    probe_cited_work_vs_container()
    probe_no_pdf_keeps_identity()
    probe_have_pdf_skips_search()
    probe_ambiguous_editable()
    probe_no_useful_footnote()
    probe_provider_failure_preserves()
    probe_evidence_paths()
    probe_identify_ingests_uploads()
    probe_extract_ingests_footnote_screenshot()
    probe_find_no_pdf_continuation_keeps_identity()
    probe_use_found_keeps_identity_and_citation()
    probe_foreign_note_no_chinese_citation()
    probe_need_more_clue_is_editable()
    probe_network_and_evidence_invariant()
    probe_no_pdf_page_renders_real_upload()
    probe_cleared_identity_field_stays_clear()
    probe_direct_upload_from_identity_screen_keeps_edits()
    probe_gbt_footnote_intake()
    probe_gbt_retry_visible_feedback()
    probe_source_resolution_safety()
    probe_gbt_parser_stays_offline()

    passed = sum(1 for entry in CHECKS if entry["ok"])
    summary = {
        "probe_count": len(CHECKS),
        "passed": passed,
        "seconds": round(time.perf_counter() - started, 1),
        "checks": CHECKS,
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for entry in CHECKS:
        mark = "PASS" if entry["ok"] else "FAIL"
        line = f"[{mark}] {entry['probe']}"
        if entry["detail"]:
            line += f"  ({entry['detail']})"
        print(line)
    print(f"\n{passed}/{len(CHECKS)} footnote-first probes passed in {summary['seconds']}s")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    raise SystemExit(main())

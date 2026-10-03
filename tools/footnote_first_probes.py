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

import json
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

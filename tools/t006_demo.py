#!/usr/bin/env python
"""T006 experimental demo harness: one command, two honest stages.

Stage 1 — **text-layer scan** (zero cost, no model call):
    The product's first question about any candidate source is whether it can be
    searched at all. On the T005B-01 facsimile the answer is ``needs_ocr``, and
    this stage prints exactly that instead of pretending a passage was found.

Stage 2 — **experimental OCR evidence** (only when an OCR cache exists):
    Retrieval runs over OCR text with the pinned *local* embedding and no LLM
    call, then the unchanged T004 evidence builder turns each retrieved passage
    into a product object with page provenance, highlighted original-page images
    and metadata-honest citation shells.

Everything is local: no paid service, no upload, no new product architecture.
The only artifact written outside private data is this script and its docs;
all page images, OCR text and evidence objects stay under ``data/private/``.

Usage (from the repository root):

    .venv\\Scripts\\python.exe tools\\t006_demo.py \\
        --pdf data/private/T005B-01/source/T005B-01_source.pdf \\
        --ocr-cache data/private/T006-01/ocr/rapidocr \\
        --out-dir data/private/T006-01/demo

Then open ``data/private/T006-01/demo/evidence_report.html``.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import t003_evidence_localize as ev  # noqa: E402
import t005b_scan_probe as scan_probe  # noqa: E402
import t006_ocr_evidence as oe  # noqa: E402
import t006_ocr_pipeline as pipeline  # noqa: E402


def stage_one(pdf_path: Path) -> dict:
    """Zero-cost text-layer scan: the product's honest first gate."""
    scan = scan_probe.scan(pdf_path)
    return {
        "pdf": oe.repo_relative(pdf_path),
        "pdf_sha256": scan_probe.sha256_of(pdf_path),
        "page_count": scan["page_count"],
        "pages_with_usable_text_layer": scan["pages_with_usable_text_layer"],
        "total_normalized_chars": scan["total_normalized_chars"],
        "seconds": scan["scan_seconds"],
        "status": (
            "searchable"
            if scan["pages_with_usable_text_layer"]
            else "needs_ocr"
        ),
    }


def render_demo(summary: dict, stage1: dict, objects: list[dict], query: str) -> str:
    parts: list[str] = []
    parts.append("<!doctype html><html lang='zh'><meta charset='utf-8'>")
    parts.append(
        "<title>T006 experimental demo</title><style>"
        "body{font-family:system-ui,'Microsoft YaHei',sans-serif;max-width:1100px;"
        "margin:24px auto;line-height:1.6}"
        "h1,h2{border-bottom:1px solid #ddd;padding-bottom:6px}"
        ".status{display:inline-block;padding:2px 8px;border-radius:10px;"
        "font-size:12px;color:#fff;margin-left:6px}"
        ".located{background:#2e7d32}.ambiguous{background:#ef6c00}"
        ".unmatched{background:#c62828}.needs_ocr{background:#455a64}"
        ".warn{background:#fff8e1;border-left:4px solid #ffb300;padding:8px}"
        ".ok{background:#e8f5e9;border-left:4px solid #2e7d32;padding:8px}"
        "img{max-width:100%;border:1px solid #ccc;margin-top:8px}"
        "pre{white-space:pre-wrap;background:#f6f6f6;padding:8px}"
        "table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:4px 8px}"
        "</style>"
    )
    parts.append("<h1>T006 实验性演示：扫描本 → OCR → 可核查证据</h1>")
    parts.append(
        "<p class='warn'><b>实验性演示，不是最终产品界面，也不是 OCR 正式采纳。</b>"
        "OCR 文本必须与页面图像核对后才能作为引用证据。</p>"
    )

    parts.append("<h2>输入（二手文献线索，永不作为证据）</h2>")
    parts.append(f"<pre>{html.escape(query)}</pre>")

    parts.append("<h2>阶段 1：文本层扫描（0 成本，无模型调用）</h2>")
    parts.append(
        "<table><tr><th>字段</th><th>值</th></tr>"
        + "".join(
            f"<tr><td>{html.escape(key)}</td><td>{html.escape(str(value))}</td></tr>"
            for key, value in stage1.items()
        )
        + "</table>"
    )
    if stage1["status"] == "needs_ocr":
        parts.append(
            "<p class='warn'>阶段 1 结论：<b>needs_ocr</b> —— 该来源没有任何可用文本层，"
            "默认路径如实报告失败，不编造引文、页码或高亮。</p>"
        )
    else:
        parts.append("<p class='ok'>阶段 1 结论：来源可直接检索。</p>")

    parts.append("<h2>阶段 2：实验性 OCR 证据路径</h2>")
    parts.append(
        "<table><tr><th>字段</th><th>值</th></tr>"
        + "".join(
            f"<tr><td>{html.escape(key)}</td><td>{html.escape(str(summary[key]))}</td></tr>"
            for key in (
                "ocr_engine",
                "ocr_pages",
                "ocr_pages_without_text",
                "ocr_total_chars",
                "chunk_count",
                "retrieval",
                "embedding",
                "k",
                "model_calls",
                "cost_usd",
            )
        )
        + "</table>"
    )

    for obj in objects:
        parts.append("<hr>")
        parts.append(
            f"<h3>{html.escape(obj['candidate_id'])}"
            f"<span class='status {obj['status']}'>{obj['status']}</span></h3>"
        )
        parts.append(
            "<table>"
            f"<tr><td>检索页标签</td><td>{html.escape(str(obj.get('retrieval_page_label')))}</td></tr>"
            f"<tr><td>解析到的 PDF 页</td><td>{obj['pdf_page_numbers']}</td></tr>"
            "<tr><td>印刷页码</td><td>未解析（绝不用 PDF 页号顶替）</td></tr>"
            f"<tr><td>脚注</td><td>{html.escape(str(obj.get('basic_footnote_citation')))}</td></tr>"
            f"<tr><td>参考文献</td><td>{html.escape(str(obj.get('basic_reference_citation')))}</td></tr>"
            "</table>"
        )
        if obj.get("original_text"):
            parts.append(
                "<p><b>检索到的原文（OCR，需与页面图像核对）</b></p><pre>"
                + html.escape(obj["original_text"])
                + "</pre>"
            )
        for warning in obj.get("warnings", []):
            parts.append(f"<p class='warn'>{html.escape(warning)}</p>")
        for ref in obj.get("highlighted_image_refs", []):
            parts.append(
                f"<div><img src='{html.escape(_rel(ref))}' alt='highlighted page'></div>"
            )
    parts.append("</html>")
    return "\n".join(parts)


def _rel(ref: str) -> str:
    try:
        return str(Path(ref).resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(Path(ref))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--ocr-cache", type=Path, default=oe.DEFAULT_CACHE_DIR)
    parser.add_argument("--metadata", type=Path, default=pipeline.DEFAULT_METADATA)
    parser.add_argument("--query-file", type=Path, default=pipeline.DEFAULT_QUERY)
    parser.add_argument("--settings", type=Path, default=pipeline.DEFAULT_SETTINGS)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "data/private/T006-01/demo")
    parser.add_argument("--dpi", type=float, default=ev.DEFAULT_DPI)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--docname", default="T005B-01-plato-republic-ocr")
    parser.add_argument(
        "--citation",
        default="柏拉图《理想国》，郭斌和、张竹明译，商务印书馆1986（扫描本，OCR）",
    )
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    query = args.query_file.read_text(encoding="utf-8").strip()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))

    stage1 = stage_one(args.pdf)
    print(json.dumps(stage1, ensure_ascii=True, indent=2), flush=True)

    summary = pipeline.run(
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
    objects = json.loads(
        (args.out_dir / "evidence_objects.json").read_text(encoding="utf-8")
    )
    report = render_demo(summary, stage1, objects, query)
    (args.out_dir / "demo_report.html").write_text(report, encoding="utf-8")
    (args.out_dir / "demo_stage1_scan.json").write_text(
        json.dumps(stage1, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "started_at": started,
                "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "report": oe.repo_relative(args.out_dir / "demo_report.html"),
                "statuses": summary["statuses"],
                "located_pages": summary["located_pages"],
                "model_calls": 0,
                "cost_usd": 0.0,
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

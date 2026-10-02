#!/usr/bin/env python
"""Live benchmark for the lawful source-acquisition finder (Phase 1).

Requires network. Runs the three required benchmark cases, downloads the PDFs
that are genuinely open, validates them, and (optionally) feeds the smallest
downloaded PDF through the *unchanged* canonical pipeline to prove that an
acquired file enters the existing evidence path.

Run:

    .venv\\Scripts\\python.exe tools\\sa_benchmark.py
    .venv\\Scripts\\python.exe tools\\sa_benchmark.py --with-pipeline

Nothing here is a paid call: the finder uses only keyless public interfaces and
the pipeline uses the local embedding with no LLM.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import pypdfium2 as pdfium  # noqa: E402

import mvp_pipeline as mvp  # noqa: E402
import source_acquisition as sa  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "data/private/sa_benchmark"

# The three cases the Phase 1 brief requires:
#   open  - a known public-domain book where a lawful PDF should be obtainable
#   oa    - a scholarly open-access book/chapter through a scholarly adapter
#   closed- an in-copyright translation that must honestly ask for an upload
CASES = (
    {
        "case_id": "open_pd_book",
        "query": "The Republic Plato 1894",
        "expect": sa.ACCESS_OPEN_PDF,
        "download": True,
    },
    {
        "case_id": "oa_scholarly_book",
        "query": "A Philosophy of Intellectual Property",
        "expect": sa.ACCESS_OPEN_PDF,
        "download": True,
    },
    {
        "case_id": "closed_translation",
        "query": "理想国 郭斌和 张竹明",
        "expect": sa.ACCESS_USER_UPLOAD,
        "download": False,
    },
)


def _pdf_page_count(path: Path) -> int:
    document = pdfium.PdfDocument(str(path))
    try:
        return len(document)
    finally:
        document.close()


def _sample_quote(path: Path) -> str:
    """A secondary-text stand-in: a real sentence read from the acquired PDF."""
    document = pdfium.PdfDocument(str(path))
    try:
        for index in range(len(document)):
            page = document[index]
            text = page.get_textpage().get_text_range()
            cleaned = " ".join((text or "").split())
            if len(cleaned) >= 220:
                return cleaned[40:260]
    finally:
        document.close()
    return ""


def run_case(case: dict, out_dir: Path, *, limit: int = 4) -> dict:
    started = time.perf_counter()
    record: dict = {"case_id": case["case_id"], "query": case["query"]}
    sa.reset_http_counter()
    try:
        payload = sa.search_all(case["query"], limit=limit)
    except Exception as error:  # noqa: BLE001 - reported, not hidden
        record.update({"ok": False, "error": f"{type(error).__name__}: {error}"})
        return record
    record["http_calls"] = sa.HTTP_CALLS

    eligible = [item for item in payload["results"] if item.get("evidence_eligible")]
    record["outcome"] = payload["outcome"]["status"]
    record["outcome_message"] = payload["outcome"]["message"]
    record["providers"] = payload["providers"]
    record["result_count"] = len(payload["results"])
    record["evidence_eligible_count"] = len(eligible)
    record["top_results"] = [
        {
            "provider": item.get("source_provider"),
            "title": item.get("title"),
            "year": item.get("year"),
            "access_status": item.get("access_status"),
            "match_score": item.get("match_score"),
            "pdf_url": item.get("pdf_url"),
            "license": item.get("license"),
            "reason": item.get("reason_not_evidence_eligible"),
        }
        for item in payload["results"][:6]
    ]
    record["outcome_as_expected"] = payload["outcome"]["status"] == case["expect"]

    if case["download"] and eligible:
        # A provider's "pdf_url" is a claim, not a guarantee: OpenAlex in
        # particular sometimes points at a landing page. Try successive
        # candidates, and record every attempt so the failure rate is visible.
        attempts = []
        record["download"] = {"ok": False, "error": "no candidate downloaded"}
        for chosen in eligible[:3]:
            attempt = {"provider": chosen.get("source_provider"), "pdf_url": chosen.get("pdf_url")}
            try:
                saved = sa.download_open_pdf(chosen, out_dir / case["case_id"])
            except (sa.DownloadRefused, sa.ProviderError) as error:
                attempt["error"] = f"{type(error).__name__}: {error}"
                attempts.append(attempt)
                continue
            target = Path(saved["path"])
            pages = _pdf_page_count(target)
            attempt["ok"] = pages > 0
            attempts.append(attempt)
            record["download"] = {
                "ok": pages > 0,
                "path": mvp.repo_relative(target),
                "bytes": saved["bytes"],
                "sha256": saved["sha256"],
                "pages": pages,
                "provider": saved["source_provider"],
                "license": saved["license"],
                "pdf_url": saved["pdf_url"],
                "landing_url": saved["landing_url"],
                "first_bytes_are_pdf": target.read_bytes()[:4] == sa.PDF_MAGIC,
            }
            sa.write_provenance(saved, target.with_suffix(".provenance.json"))
            break
        record["download_attempts"] = attempts
    record["seconds"] = round(time.perf_counter() - started, 1)
    return record


def run_pipeline_check(downloaded: list[Path], out_dir: Path, *, k: int = 5) -> dict:
    """Feed the smallest acquired PDF through the unchanged canonical pipeline."""
    candidates = sorted(
        (path for path in downloaded if path.exists()), key=lambda path: path.stat().st_size
    )
    if not candidates:
        return {"ok": False, "error": "no downloaded PDF available"}
    target = candidates[0]
    secondary = _sample_quote(target)
    if not secondary:
        return {"ok": False, "error": f"no quotable text layer in {target.name}"}
    result = mvp.run_pipeline(
        secondary_text=secondary,
        hints="",
        source={
            "source_id": target.stem,
            "label": f"open-source finder download: {target.name}",
            "pdf": str(target),
            "metadata": {},
            "docname": target.stem,
        },
        out_dir=out_dir / "pipeline_run",
        retrieval_mode="local",
        ocr_mode="auto",
        k=k,
        log=lambda message: print(f"    [pipeline] {message}"),
    )
    located = [item for item in result["candidates"] if item["status"] == "located"]
    return {
        "ok": bool(located),
        "source_file": target.name,
        "secondary_chars": len(secondary),
        "result_state": result["result_state"]["state"],
        "route": result["source"]["route"],
        "page_count": result["source"]["page_count"],
        "chunk_count": result["run"].get("chunk_count"),
        "candidates": result["counts"]["candidates"],
        "located": result["counts"]["located"],
        "highlight_images": result["counts"]["highlight_images"],
        "model_calls": result["run"]["model_calls"],
        "cost_usd": result["run"]["cost_usd"],
        "out_dir": mvp.repo_relative(out_dir / "pipeline_run"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--with-pipeline", action="store_true")
    parser.add_argument(
        "--pipeline-only",
        action="store_true",
        help="skip the network cases and reuse PDFs already in --out-dir",
    )
    args = parser.parse_args(argv)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = out_dir / "benchmark.json"
    if args.pipeline_only and existing.exists():
        report: dict = json.loads(existing.read_text(encoding="utf-8"))
        report.pop("pipeline", None)
        downloaded = [path for path in out_dir.rglob("*.pdf")]
        print(f"reusing {len(downloaded)} downloaded PDF(s) from {mvp.repo_relative(out_dir)}")
    else:
        report = {
            "benchmark": "sa-phase1",
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "cases": [],
            "model_calls": 0,
            "cost_usd": 0.0,
        }
        downloaded = []
    for case in (() if args.pipeline_only else CASES):
        print(f"== {case['case_id']}: {case['query']}")
        record = run_case(case, out_dir, limit=args.limit)
        report["cases"].append(record)
        print(
            f"   outcome={record.get('outcome')} eligible={record.get('evidence_eligible_count')}"
            f" expected={case['expect']} match={record.get('outcome_as_expected')}"
            f" ({record.get('seconds')}s)"
        )
        for entry in record["providers"]:
            state = f"ok {entry.get('count')}" if entry.get("ok") else "FAIL"
            print(f"     {entry['provider']:<17} {state}")
        for top in record["top_results"][:4]:
            print(
                f"     - [{top['access_status']}] m={top['match_score']} "
                f"{str(top['title'])[:58]}"
            )
        download = record.get("download")
        if download:
            print(f"     download: {download}")
            if download.get("ok"):
                downloaded.append(REPO_ROOT / str(download["path"]))

    if args.with_pipeline or args.pipeline_only:
        print("== pipeline integration")
        report["pipeline"] = run_pipeline_check(downloaded, out_dir, k=args.k)
        print(f"   {report['pipeline']}")

    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (out_dir / "benchmark.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"report: {mvp.repo_relative(out_dir / 'benchmark.json')}")
    failures = [c for c in report["cases"] if not c.get("outcome_as_expected")]
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

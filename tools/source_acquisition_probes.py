#!/usr/bin/env python
"""Zero-cost acceptance probes for the lawful source-acquisition finder.

Deterministic, offline and free: no network, no model call, no paid API and no
private source material. Provider responses are injected as fixtures, and the
download path is exercised against a throwaway loopback HTTP server, so the
suite can run in the normal regression set on a machine with no egress.

Run:

    .venv\\Scripts\\python.exe tools\\source_acquisition_probes.py
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import source_acquisition as sa  # noqa: E402
import mvp_app as app  # noqa: E402
import mvp_pipeline as mvp  # noqa: E402

WORK_DIR = REPO_ROOT / "data/private/sa_probes"
SUMMARY_PATH = WORK_DIR / "source_acquisition_probe_summary.json"

MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)

CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append({"probe": name, "ok": bool(ok), "detail": detail})


class _PayloadHandler(BaseHTTPRequestHandler):
    payload = b""
    content_type = "application/octet-stream"

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        self.send_response(200)
        self.send_header("Content-Type", type(self).content_type)
        self.send_header("Content-Length", str(len(type(self).payload)))
        self.end_headers()
        self.wfile.write(type(self).payload)

    def log_message(self, *args) -> None:  # noqa: D102 - silence test server
        return


def _serve(payload: bytes, content_type: str):
    handler = type(
        "Handler",
        (_PayloadHandler,),
        {"payload": payload, "content_type": content_type},
    )
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}/file"


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

DSpace_FIXTURE = {
    "_embedded": {
        "searchResult": {
            "_embedded": {
                "objects": [
                    {
                        "_embedded": {
                            "indexableObject": {
                                "uuid": "9c1f-uuid",
                                "name": "An Open Access Book",
                                "handle": "20.500.12657/12345",
                                "metadata": {
                                    "dc.title": [{"value": "An Open Access Book"}],
                                    "dc.contributor.author": [
                                        {"value": "Doe, Jane"},
                                        {"value": "Roe, Richard"},
                                    ],
                                    "dc.date.issued": [{"value": "2019-04-01"}],
                                    "dc.identifier.isbn": [{"value": "9789462980000"}],
                                    "dc.identifier.doi": [{"value": "10.1234/oab.2019"}],
                                    "dc.language.iso": [{"value": "eng"}],
                                    "dc.rights.uri": [
                                        {"value": "https://creativecommons.org/licenses/by/4.0/"}
                                    ],
                                    "dc.description.abstract": [{"value": "An abstract."}],
                                    "dc.publisher": [{"value": "Example Press"}],
                                },
                            }
                        }
                    }
                ]
            }
        }
    }
}

GOOGLE_BOOKS_FIXTURE = {
    "items": [
        {
            "id": "pd-volume",
            "volumeInfo": {
                "title": "The Republic",
                "authors": ["Plato"],
                "publishedDate": "1894",
                "language": "en",
                "infoLink": "https://books.google.com/books?id=pd-volume",
                "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780000000001"}],
            },
            "accessInfo": {
                "viewability": "ALL_PAGES",
                "publicDomain": True,
                "embeddable": True,
                "pdf": {"isAvailable": True, "downloadLink": "https://example.org/pd.pdf"},
                "epub": {"isAvailable": False},
            },
        },
        {
            "id": "preview-volume",
            "volumeInfo": {"title": "A Modern Commentary", "authors": ["Someone"]},
            "accessInfo": {
                "viewability": "PARTIAL",
                "publicDomain": False,
                "embeddable": True,
                "pdf": {"isAvailable": False},
                "epub": {"isAvailable": False},
            },
        },
    ]
}

OPENALEX_FIXTURE = {
    "results": [
        {
            "id": "https://openalex.org/W1",
            "doi": "https://doi.org/10.5678/oa.2021",
            "title": "An Open Access Chapter",
            "publication_year": 2021,
            "language": "en",
            "type": "book-chapter",
            "open_access": {"oa_status": "gold"},
            "authorships": [{"author": {"display_name": "Ada Author"}}],
            "best_oa_location": {
                "is_oa": True,
                "pdf_url": "https://example.org/chapter.pdf",
                "landing_page_url": "https://example.org/chapter",
                "license": "cc-by",
            },
        },
        {
            "id": "https://openalex.org/W2",
            "title": "A Landing Page Only Work",
            "publication_year": 2018,
            "open_access": {"oa_status": "green"},
            "authorships": [],
            "best_oa_location": {
                "is_oa": True,
                "pdf_url": None,
                "landing_page_url": "https://example.org/landing",
                "license": None,
            },
        },
    ]
}


# --------------------------------------------------------------------------- #
# probes
# --------------------------------------------------------------------------- #


def probe_schema() -> None:
    record = sa._record(source_provider="x", title="t")
    required = {
        "source_provider",
        "title",
        "authors",
        "year",
        "language",
        "identifiers",
        "access_status",
        "license",
        "landing_url",
        "pdf_url",
        "pdf_hint",
        "evidence_eligible",
        "reason_not_evidence_eligible",
        "match_score",
        "provider_record",
    }
    check("schema_has_all_keys", required <= set(record), str(sorted(required - set(record))))
    check("schema_default_is_not_evidence", record["evidence_eligible"] is False)
    check(
        "schema_default_gives_a_reason",
        bool(record["reason_not_evidence_eligible"]),
        str(record["reason_not_evidence_eligible"]),
    )


def probe_eligibility_rule() -> None:
    eligible = sa._record(access_status=sa.ACCESS_OPEN_PDF, pdf_url="https://x/y.pdf")
    check("open_pdf_with_url_is_eligible", eligible["evidence_eligible"] is True)
    pdf_no_url = sa._record(access_status=sa.ACCESS_OPEN_PDF)
    check(
        "open_pdf_without_url_is_not_eligible",
        pdf_no_url["evidence_eligible"] is False
        and "no direct PDF URL" in str(pdf_no_url["reason_not_evidence_eligible"]),
        str(pdf_no_url["reason_not_evidence_eligible"]),
    )
    for status in (
        sa.ACCESS_OPEN_PAGE,
        sa.ACCESS_METADATA_ONLY,
        sa.ACCESS_USER_UPLOAD,
        sa.ACCESS_ERROR,
        sa.ACCESS_RATE_LIMIT,
    ):
        record = sa._record(access_status=status, pdf_url="https://x/y.pdf")
        check(
            f"not_evidence_eligible::{status}",
            record["evidence_eligible"] is False,
            str(record["reason_not_evidence_eligible"]),
        )


def probe_outcome_classification() -> None:
    empty = sa.classify_outcome([])
    check("empty_query_asks_for_upload", empty["status"] == sa.ACCESS_USER_UPLOAD, empty["status"])

    failed = sa.classify_outcome([], [{"provider": "a", "ok": False, "error": "boom"}])
    check("all_providers_failed_is_error", failed["status"] == sa.ACCESS_ERROR, failed["status"])

    relevant_pdf = [
        sa._record(
            source_provider="x",
            title="Plato Republic",
            access_status=sa.ACCESS_OPEN_PDF,
            pdf_url="https://x/y.pdf",
            match_score=0.8,
        )
    ]
    check(
        "relevant_open_pdf_is_announced",
        sa.classify_outcome(relevant_pdf)["status"] == sa.ACCESS_OPEN_PDF,
    )

    # Regression for the first live run: querying a closed Chinese translation
    # returned unrelated open PDFs with zero term overlap, which must NOT be
    # announced as the user's source.
    irrelevant = [
        sa._record(
            source_provider="openalex",
            title="Driving forces of wetland change in China",
            access_status=sa.ACCESS_OPEN_PDF,
            pdf_url="https://x/y.pdf",
            match_score=0.0,
        )
    ]
    outcome = sa.classify_outcome(irrelevant, [{"provider": "openalex", "ok": True, "count": 1}])
    check(
        "irrelevant_open_pdf_falls_back_to_upload",
        outcome["status"] == sa.ACCESS_USER_UPLOAD,
        outcome["status"],
    )

    relevant_preview = [
        sa._record(source_provider="ia", title="理想国", match_score=0.6)
    ]
    outcome = sa.classify_outcome(relevant_preview, [{"provider": "ia", "ok": True, "count": 1}])
    check(
        "relevant_metadata_asks_for_upload",
        outcome["status"] == sa.ACCESS_METADATA_ONLY,
        outcome["status"],
    )


def probe_relevance_hint() -> None:
    check(
        "query_terms_cjk_bigrams",
        sa.query_terms("理想国") == ["理想", "想国"],
        str(sa.query_terms("理想国")),
    )
    check(
        "query_terms_latin_words",
        sa.query_terms("Plato Republic") == ["plato", "republic"],
        str(sa.query_terms("Plato Republic")),
    )
    check(
        "match_score_hits",
        sa.match_score("Plato Republic", {"title": "Plato's Republic", "authors": []}) == 1.0,
    )
    check(
        "match_score_misses",
        sa.match_score("理想国 柏拉图", {"title": "Wetland change in China"}) == 0.0,
    )


def probe_internet_archive_rights() -> None:
    open_cases = [
        ("not_in_copyright_underscore", {"possible-copyright-status": "NOT_IN_COPYRIGHT"}),
        ("not_in_copyright_spaces", {"rights": "Not in copyright"}),
        ("public_domain_phrase", {"rights": "Public Domain Mark 1.0"}),
        ("gutenberg_collection", {"collection": ["gutenberg"]}),
        ("americana_collection", {"collection": ["americana"]}),
    ]
    for name, meta in open_cases:
        ok, refusal = sa._ia_is_open(meta, {})
        check(f"ia_open::{name}", ok is True, str(refusal))

    refused_cases = [
        ("lending_item", {"collection": ["inlibrary"], "possible-copyright-status": "NOT_IN_COPYRIGHT"}, {}),
        ("printdisabled", {"collection": ["printdisabled", "americana"]}, {}),
        ("private_file", {"collection": ["americana"]}, {"private": True}),
        ("restricted_file", {"collection": ["americana"]}, {"access-restricted-item": True}),
        ("no_signal", {"collection": ["someones-upload"]}, {}),
    ]
    for name, meta, entry in refused_cases:
        ok, refusal = sa._ia_is_open(meta, entry)
        check(f"ia_refused::{name}", ok is False and bool(refusal), str(refusal))


def probe_dspace_normalization() -> None:
    sa.http_get_json = lambda url, params=None, **kw: DSpace_FIXTURE

    records = sa._dspace_search(
        "https://example.org", provider="oapen", query="open access book", limit=3
    )
    check("dspace_returns_one_record", len(records) == 1, str(len(records)))
    record = records[0]
    check("dspace_title", record["title"] == "An Open Access Book", str(record["title"]))
    check("dspace_authors", record["authors"] == ["Doe, Jane", "Roe, Richard"], str(record["authors"]))
    check("dspace_year", record["year"] == "2019", str(record["year"]))
    check("dspace_isbn", record["identifiers"].get("isbn") == ["9789462980000"], str(record["identifiers"]))
    check("dspace_doi", record["identifiers"].get("doi") == "10.1234/oab.2019", str(record["identifiers"]))
    check("dspace_license", "creativecommons" in str(record["license"]), str(record["license"]))
    check("dspace_starts_not_evidence", record["evidence_eligible"] is False)

    sa._dspace_bitstreams = lambda uuid, base: [
        {
            "name": "book.pdf",
            "size": 4200,
            "content_url": "https://example.org/bitstream/book.pdf",
            "mimetype": "application/pdf",
        }
    ]
    upgraded = sa._dspace_attach_pdf([dict(record)], "https://example.org")
    check(
        "dspace_pdf_upgrades_to_eligible",
        upgraded[0]["evidence_eligible"] is True
        and upgraded[0]["pdf_url"] == "https://example.org/bitstream/book.pdf",
        str(upgraded[0]["pdf_url"]),
    )

    sa._dspace_bitstreams = lambda uuid, base: [
        {
            "name": "book.epub",
            "size": 900,
            "content_url": "https://example.org/bitstream/book.epub",
            "mimetype": "application/epub+zip",
        }
    ]
    epub_only = sa._dspace_attach_pdf([dict(record)], "https://example.org")
    check(
        "dspace_epub_only_is_not_evidence",
        epub_only[0]["evidence_eligible"] is False
        and epub_only[0]["access_status"] == sa.ACCESS_OPEN_PAGE,
        str(epub_only[0]["access_status"]),
    )


def probe_google_books_normalization() -> None:
    sa.http_get_json = lambda url, params=None, **kw: GOOGLE_BOOKS_FIXTURE
    records = sa.search_google_books("Plato Republic", 2)
    check("google_books_two_records", len(records) == 2, str(len(records)))
    public_domain, preview = records
    check(
        "google_books_public_domain_pdf_is_eligible",
        public_domain["evidence_eligible"] is True
        and public_domain["pdf_url"] == "https://example.org/pd.pdf",
        str(public_domain["pdf_url"]),
    )
    check(
        "google_books_preview_is_not_eligible",
        preview["evidence_eligible"] is False
        and preview["access_status"] == sa.ACCESS_METADATA_ONLY,
        str(preview["access_status"]),
    )


def probe_openalex_normalization() -> None:
    sa.http_get_json = lambda url, params=None, **kw: OPENALEX_FIXTURE
    records = sa.search_openalex("open access chapter", 2)
    check("openalex_two_records", len(records) == 2, str(len(records)))
    with_pdf, landing_only = records
    check(
        "openalex_pdf_location_is_eligible",
        with_pdf["evidence_eligible"] is True
        and with_pdf["pdf_url"] == "https://example.org/chapter.pdf",
        str(with_pdf["pdf_url"]),
    )
    check(
        "openalex_landing_only_is_open_page",
        landing_only["evidence_eligible"] is False
        and landing_only["access_status"] == sa.ACCESS_OPEN_PAGE,
        str(landing_only["access_status"]),
    )
    check(
        "openalex_doi_is_normalized",
        with_pdf["identifiers"].get("doi") == "10.5678/oa.2021",
        str(with_pdf["identifiers"]),
    )


def probe_wikisource() -> None:
    sa.http_get_json = lambda url, params=None, **kw: {
        "query": {
            "search": [
                {
                    "ns": 0,
                    "title": "論語",
                    "pageid": 42,
                    "wordcount": 1234,
                    "snippet": "<span class='searchmatch'>論語</span> 卷一",
                }
            ]
        }
    }
    records = sa.search_wikisource("論語", 1)
    check("wikisource_returns_record", len(records) == 1, str(len(records)))
    record = records[0]
    check(
        "wikisource_is_never_evidence",
        record["evidence_eligible"] is False
        and record["access_status"] == sa.ACCESS_OPEN_PAGE,
        str(record["access_status"]),
    )
    check("wikisource_snippet_is_plain_text", "<span" not in record["provider_record"]["snippet"])
    check(
        "wikisource_landing_url",
        record["landing_url"] == "https://zh.wikisource.org/wiki/%E8%AB%96%E8%AA%9E",
        str(record["landing_url"]),
    )


def probe_provider_isolation() -> None:
    original = dict(sa.PROVIDERS)

    def boom(query, limit):
        raise sa.ProviderError("synthetic outage")

    def good(query, limit):
        return [sa._record(source_provider="good", title="Plato Republic")]

    sa.PROVIDERS = dict(original)
    sa.PROVIDERS["boom"] = boom
    sa.PROVIDERS["good"] = good
    try:
        payload = sa.search_all("Plato Republic", providers=("boom", "good"), limit=1)
    finally:
        sa.PROVIDERS = original
    report = {entry["provider"]: entry for entry in payload["providers"]}
    check("isolation_failing_provider_reported", report["boom"]["ok"] is False, str(report["boom"]))
    check("isolation_good_provider_survives", report["good"]["ok"] is True, str(report["good"]))
    check("isolation_result_kept", len(payload["results"]) == 1, str(len(payload["results"])))
    check(
        "isolation_match_score_attached",
        payload["results"][0]["match_score"] == 1.0,
        str(payload["results"][0]["match_score"]),
    )


def probe_download_guardrails(tmp_dir: Path) -> None:
    not_eligible = sa._record(
        access_status=sa.ACCESS_METADATA_ONLY,
        title="Preview only",
        reason_not_evidence_eligible="metadata only",
    )
    try:
        sa.download_open_pdf(not_eligible, tmp_dir)
        check("download_refuses_non_eligible", False, "no exception raised")
    except sa.DownloadRefused as error:
        check("download_refuses_non_eligible", True, str(error))

    scheme = sa._record(
        access_status=sa.ACCESS_OPEN_PDF, pdf_url="file:///etc/passwd", title="x"
    )
    try:
        sa.download_open_pdf(scheme, tmp_dir)
        check("download_refuses_non_http", False, "no exception raised")
    except sa.DownloadRefused as error:
        check("download_refuses_non_http", True, str(error))

    server, url = _serve(b"<html>not a pdf</html>", "text/html")
    try:
        html_record = sa._record(access_status=sa.ACCESS_OPEN_PDF, pdf_url=url, title="html")
        try:
            sa.download_open_pdf(html_record, tmp_dir)
            check("download_rejects_html", False, "no exception raised")
        except sa.DownloadRefused as error:
            check("download_rejects_html", True, str(error))
        check(
            "download_wrote_nothing_for_html",
            not any(tmp_dir.glob("*.pdf")),
            str(list(tmp_dir.iterdir())),
        )
    finally:
        server.shutdown()

    server, url = _serve(MINIMAL_PDF, "application/pdf")
    try:
        pdf_record = sa._record(
            access_status=sa.ACCESS_OPEN_PDF,
            pdf_url=url,
            title="Saved Open Book",
            source_provider="fixture",
        )
        saved = sa.download_open_pdf(pdf_record, tmp_dir)
        target = Path(saved["path"])
        check("download_saves_pdf", target.exists() and target.read_bytes().startswith(b"%PDF"))
        check("download_records_sha256", len(saved["sha256"]) == 64, saved["sha256"][:12])
        check("download_keeps_provenance", saved["pdf_url"] == url, str(saved["pdf_url"]))
        provenance = sa.write_provenance(saved, tmp_dir / "provenance.json")
        payload = json.loads(provenance.read_text(encoding="utf-8"))
        check(
            "provenance_json_round_trip",
            payload["source_provider"] == "fixture" and payload["title"] == "Saved Open Book",
            str(payload.get("title")),
        )
    finally:
        server.shutdown()


def probe_error_detail_trimming() -> None:
    raw = "<!DOCTYPE html>\n<html><body>You address is not allowed to access this API.</body></html>"
    trimmed = sa.short_error_detail(raw)
    check("error_detail_strips_html", "<" not in trimmed and ">" not in trimmed, trimmed)
    check("error_detail_keeps_message", "not allowed to access this API" in trimmed, trimmed)
    check("error_detail_truncates", len(sa.short_error_detail("x" * 500)) <= 161)


def probe_no_silent_network() -> None:
    """The finder must be reachable only from the explicit /find route."""
    app_source = (TOOLS_DIR / "mvp_app.py").read_text(encoding="utf-8")
    check(
        "app_imports_finder",
        "import source_acquisition" in app_source,
        "mvp_app must import the finder module",
    )
    check(
        "app_calls_search_all_once",
        app_source.count("sa.search_all(") == 1,
        str(app_source.count("sa.search_all(")),
    )
    check(
        "app_uses_find_route",
        '"/find"' in app_source and '"/use_found"' in app_source,
        "explicit POST routes expected",
    )
    pipeline_source = (TOOLS_DIR / "mvp_pipeline.py").read_text(encoding="utf-8")
    check(
        "pipeline_never_searches_the_web",
        "source_acquisition" not in pipeline_source,
        "the canonical pipeline must stay offline",
    )


def _post(url: str, body: bytes) -> tuple[int, str]:
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def _get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def probe_finder_http_surface(tmp_dir: Path) -> None:
    """The real product route, exercised offline with injected provider results."""
    runs = tmp_dir.parent / "http_runs"
    uploads = tmp_dir.parent / "http_uploads"
    finder = tmp_dir.parent / "http_finder"
    for directory in (runs, uploads, finder):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)

    eligible = sa._record(
        source_provider="internet_archive",
        title="Plato Republic Volume One",
        authors=["Plato"],
        year="1894",
        access_status=sa.ACCESS_OPEN_PDF,
        pdf_url="https://example.org/pd.pdf",
        license="public domain",
        landing_url="https://archive.org/details/fixture",
        match_score=1.0,
    )
    preview = sa._record(
        source_provider="google_books",
        title="A Modern Commentary",
        access_status=sa.ACCESS_METADATA_ONLY,
        reason_not_evidence_eligible="preview only; no page-grounded full text",
        match_score=0.5,
    )
    payload = {
        "query": "Plato Republic",
        "providers": [{"provider": "internet_archive", "ok": True, "count": 2}],
        "outcome": {"status": sa.ACCESS_OPEN_PDF, "message": "发现 1 个可直接下载的开放 PDF 候选"},
        "results": [eligible, preview],
    }

    saved_search = sa.search_all
    saved_download = sa.download_open_pdf
    sa.search_all = lambda query, limit=6, **kwargs: payload

    def fake_download(record, dest_dir, **kwargs):
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / "found.pdf"
        target.write_bytes(MINIMAL_PDF)
        return {
            "path": str(target),
            "bytes": len(MINIMAL_PDF),
            "source_provider": record.get("source_provider"),
            "title": record.get("title"),
            "pdf_url": record.get("pdf_url"),
            "sha256": "b" * 64,
        }

    sa.download_open_pdf = fake_download

    app.Handler.sources = mvp.load_sources()
    app.Handler.runs_dir = runs
    app.Handler.uploads_dir = uploads
    app.Handler.finder_dir = finder
    server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    base = f"http://{server.server_address[0]}:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        status, home = _get(base + "/")
        check("http_home_has_finder_entry", status == 200 and "查找开放全文" in home, str(status))
        check("http_home_keeps_upload_path", "upload" in home or "上传一手文献" in home)

        body = urllib.parse.urlencode(
            {"find_query": "Plato Republic", "secondary_text": "某二手作者的转述文本。", "hints": ""}
        ).encode("utf-8")
        status, find_html = _post(base + "/find", body)
        check("http_find_returns_page", status == 200, str(status))
        check("http_find_lists_candidate", "Plato Republic Volume One" in find_html)
        check("http_find_offers_download", "/use_found" in find_html)
        check("http_find_refuses_preview", "不能作为页码可核验" in find_html)
        check("http_find_shows_provider_line", "Internet Archive" in find_html)

        token_match = re.search(r"name='token' value='([0-9a-f-]+)'", find_html)
        token = token_match.group(1) if token_match else ""
        check("http_find_issues_token", bool(token), token)

        body = urllib.parse.urlencode(
            {"token": token, "index": "0", "secondary_text": "某二手作者的转述文本。", "hints": ""}
        ).encode("utf-8")
        status, confirm = _post(base + "/use_found", body)
        check(
            "http_use_found_reaches_confirm",
            status == 200 and "确认要检索的文本" in confirm,
            str(status),
        )
        check(
            "http_use_found_attaches_pdf",
            "primary_upload" in confirm and "found.pdf" in confirm,
            "confirm page must carry the downloaded PDF",
        )
        check("http_use_found_saved_pdf", any(uploads.rglob("found.pdf")))
        check("http_use_found_saved_provenance", any(uploads.rglob("*.provenance.json")))

        body = urllib.parse.urlencode(
            {"token": "20260101-000000-abcdef", "index": "0", "secondary_text": "x"}
        ).encode("utf-8")
        status, stale = _post(base + "/use_found", body)
        check("http_use_found_rejects_forged_token", status == 200 and "失效" in stale, str(status))

        body = urllib.parse.urlencode({"find_query": "", "secondary_text": ""}).encode("utf-8")
        status, empty = _post(base + "/find", body)
        check("http_find_needs_a_query", status == 200 and "请先填写" in empty, str(status))
    finally:
        server.shutdown()
        sa.search_all = saved_search
        sa.download_open_pdf = saved_download


def main() -> int:
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    tmp_dir = WORK_DIR / "downloads"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    saved_get_json = sa.http_get_json
    try:
        probe_schema()
        probe_eligibility_rule()
        probe_outcome_classification()
        probe_relevance_hint()
        probe_internet_archive_rights()
        probe_dspace_normalization()
        probe_google_books_normalization()
        probe_openalex_normalization()
        probe_wikisource()
        probe_provider_isolation()
        probe_download_guardrails(tmp_dir)
        probe_error_detail_trimming()
        probe_no_silent_network()
        probe_finder_http_surface(tmp_dir)
    finally:
        sa.http_get_json = saved_get_json
        sa._dspace_bitstreams = _ORIGINAL_BITSTREAMS

    passed = sum(1 for entry in CHECKS if entry["ok"])
    total = len(CHECKS)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(
            {"passed": passed, "total": total, "checks": CHECKS},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    for entry in CHECKS:
        if not entry["ok"]:
            print(f"FAIL {entry['probe']}: {entry['detail']}")
    print(f"source-acquisition probes: {passed}/{total}")
    return 0 if passed == total else 1


_ORIGINAL_BITSTREAMS = sa._dspace_bitstreams

if __name__ == "__main__":
    sys.exit(main())

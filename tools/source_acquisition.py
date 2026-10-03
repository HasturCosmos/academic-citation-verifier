"""Lawful open-source finder (post-MVP source acquisition, Phase 1).

Experimental, reversible and *offline-by-default*: nothing here runs unless a
caller explicitly asks it to. The module answers one narrow question:

    "The user has no primary-source PDF. Is a genuinely open / lawfully
    downloadable full-text PDF available through a maintained public
    interface?"

Design rules that the rest of the product depends on:

* only official public interfaces are used; no paid service, no API key, no
  account, no login, no borrowing, no paywall/DRM/access-control bypass;
* a record is ``evidence_eligible`` **only** when it carries a direct,
  clearly-open PDF URL. Metadata records, previews, snippets, EPUB-only
  resources and borrow-restricted items are *discovery hints* and can never
  become page-grounded evidence;
* open-access eligibility is judged from an explicit rights signal, never from
  a broad collection or a work-level flag: Internet Archive needs an explicit
  public-domain/open-licence signal (only Project Gutenberg is trusted on
  collection membership alone), and an OpenAlex PDF is eligible only when the
  location that carries that PDF is itself marked open access;
* a downloaded file is accepted only after the ``%PDF`` header check, and it
  is written under the git-ignored ``data/private/`` tree only;
* no page number or source text is ever invented from a provider response.

The normalized record schema is intentionally small:

    source_provider, title, authors, year, identifiers, language,
    access_status, license, landing_url, pdf_url, pdf_hint,
    evidence_eligible, reason_not_evidence_eligible, provider_record

``access_status`` is one of:

    OPEN_PDF_AVAILABLE          direct open PDF (evidence eligible)
    OPEN_PAGE_SOURCE_AVAILABLE  open full text, but not a directly usable PDF
    METADATA_OR_PREVIEW_ONLY    bibliographic record / preview / snippet
    USER_UPLOAD_REQUIRED        nothing lawful is available for this query
    ERROR / RATE_LIMIT          provider could not be asked

Diagnostics / live check:

    .venv\\Scripts\\python.exe tools\\source_acquisition.py search --query "..."
    .venv\\Scripts\\python.exe tools\\source_acquisition.py probe --query "..."
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

USER_AGENT = "academic-citation-verifier/0.1 (local research tool; lawful OA only)"
DEFAULT_TIMEOUT = 30
DEFAULT_LIMIT = 5
PDF_MAGIC = b"%PDF"
MAX_DOWNLOAD_BYTES = 300 * 1024 * 1024

ACCESS_OPEN_PDF = "OPEN_PDF_AVAILABLE"
ACCESS_OPEN_PAGE = "OPEN_PAGE_SOURCE_AVAILABLE"
ACCESS_METADATA_ONLY = "METADATA_OR_PREVIEW_ONLY"
ACCESS_USER_UPLOAD = "USER_UPLOAD_REQUIRED"
ACCESS_ERROR = "ERROR"
ACCESS_RATE_LIMIT = "RATE_LIMIT"

EVIDENCE_ELIGIBLE_STATUSES = (ACCESS_OPEN_PDF,)

# A cheap, explainable relevance hint: the fraction of query terms (Latin
# words + CJK bigrams) that appear in a record's title/authors. It is used only
# to rank and to avoid announcing an unrelated open PDF as "your source". It is
# never a claim that a record *is* the source the user means.
RELEVANCE_FLOOR = 0.5

OPENALEX_API = "https://api.openalex.org"
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"
OAPEN_BASE = "https://library.oapen.org"
DOAB_BASE = "https://directory.doabooks.org"
WIKISOURCE_API = "https://zh.wikisource.org/w/api.php"
INTERNET_ARCHIVE_SEARCH = "https://archive.org/advancedsearch.php"
INTERNET_ARCHIVE_METADATA = "https://archive.org/metadata"

RETRY_STATUSES = {429, 500, 502, 503, 504}
RETRY_DELAYS = (1.5, 4.0)

# Diagnostics: how many HTTP requests a search actually costs. Reset by
# ``reset_http_counter()``; the benchmark reports it for the cost section.
HTTP_CALLS = 0


def reset_http_counter() -> None:
    global HTTP_CALLS
    HTTP_CALLS = 0


class ProviderError(RuntimeError):
    """A provider could not be queried. Never treated as "no result"."""

    def __init__(self, message: str, *, status: str = ACCESS_ERROR) -> None:
        super().__init__(message)
        self.status = status


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #


def _build_url(url: str, params: dict | None) -> str:
    if not params:
        return url
    encoded = urllib.parse.urlencode(params, doseq=True)
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{encoded}"


def short_error_detail(raw: str, *, limit: int = 160) -> str:
    """Compact an error body for user-facing text (HTML pages are unreadable)."""
    text = re.sub(r"<[^>]+>", " ", str(raw or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def http_get(
    url: str,
    params: dict | None = None,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = len(RETRY_DELAYS),
) -> tuple[bytes, str]:
    """Fetch a public URL with a descriptive user agent. No credentials, ever."""
    global HTTP_CALLS
    final = _build_url(url, params)
    request = urllib.request.Request(
        final,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    last: ProviderError | None = None
    for attempt in range(retries + 1):
        HTTP_CALLS += 1
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.geturl()
        except urllib.error.HTTPError as error:
            detail = ""
            try:
                detail = error.read()[:300].decode("utf-8", "replace")
            except Exception:  # noqa: BLE001 - diagnostics only
                detail = ""
            detail = short_error_detail(detail)
            status = ACCESS_RATE_LIMIT if error.code == 429 else ACCESS_ERROR
            if error.code in RETRY_STATUSES:
                last = ProviderError(f"HTTP {error.code} from {final}", status=status)
                if attempt < retries:
                    time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])
                    continue
                raise ProviderError(
                    f"HTTP {error.code} from {final} after {retries + 1} attempts: "
                    + detail.strip(),
                    status=status,
                ) from error
            raise ProviderError(
                f"HTTP {error.code} from {final}: {detail}".strip()
            ) from error
        except urllib.error.URLError as error:
            last = ProviderError(f"network error for {final}: {error.reason}")
            if attempt < retries:
                time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])
                continue
            raise ProviderError(f"network error for {final}: {error.reason}") from error
    raise last or ProviderError(f"could not query {final}")


def http_get_json(url: str, params: dict | None = None, *, timeout: int = DEFAULT_TIMEOUT):
    payload, _ = http_get(url, params, timeout=timeout)
    return _decode_json(payload, url)


def _decode_json(payload: bytes, url: str):
    try:
        return json.loads(payload.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ProviderError(f"non-UTF-8 response from {url}") from error
    except json.JSONDecodeError as error:
        raise ProviderError(f"non-JSON response from {url}: {error}") from error


def _record(**fields) -> dict:
    """Normalized record with every schema key present."""
    base = {
        "source_provider": None,
        "title": None,
        "authors": [],
        "year": None,
        "language": None,
        "identifiers": {},
        "access_status": ACCESS_METADATA_ONLY,
        "license": None,
        "landing_url": None,
        "pdf_url": None,
        "pdf_hint": None,
        "evidence_eligible": False,
        "reason_not_evidence_eligible": None,
        "match_score": 0.0,
        "provider_record": {},
    }
    base.update(fields)
    return recompute_eligibility(base)


def recompute_eligibility(record: dict) -> dict:
    """Re-derive ``evidence_eligible`` after a record has been upgraded.

    The rule is deliberately strict: an OPEN_PDF status is not enough on its
    own, the record must also carry a direct PDF URL. This keeps the promise
    that only a genuinely downloadable open PDF can reach the evidence layer.
    """
    record["evidence_eligible"] = (
        record.get("access_status") in EVIDENCE_ELIGIBLE_STATUSES
        and bool(record.get("pdf_url"))
    )
    if (
        not record["evidence_eligible"]
        and record.get("access_status") in EVIDENCE_ELIGIBLE_STATUSES
        and not record.get("pdf_url")
    ):
        record["reason_not_evidence_eligible"] = (
            "open access indicated, but no direct PDF URL was found"
        )
    if not record["evidence_eligible"] and not record.get("reason_not_evidence_eligible"):
        record["reason_not_evidence_eligible"] = _default_reason(
            str(record.get("access_status"))
        )
    return record


def _default_reason(status: str) -> str:
    return {
        ACCESS_OPEN_PAGE: "open full text exists but no directly usable PDF URL",
        ACCESS_METADATA_ONLY: "metadata/preview only; no page-grounded full text",
        ACCESS_USER_UPLOAD: "no lawful open full text found for this query",
        ACCESS_ERROR: "provider could not be queried",
        ACCESS_RATE_LIMIT: "provider rate-limited the request",
    }.get(status, "not evidence eligible")


def _clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _year_from(value) -> str | None:
    text = _clean(value)
    if not text:
        return None
    match = re.search(r"(1[5-9]\d\d|20\d\d)", text)
    return match.group(1) if match else None


def _is_pdf_url(url: str | None) -> bool:
    if not url:
        return False
    path = urllib.parse.urlparse(url).path.lower()
    return path.endswith(".pdf")


def query_terms(query: str) -> list[str]:
    """Latin words and CJK bigrams used for the cheap relevance hint."""
    text = (query or "").lower()
    latin = re.findall(r"[a-z0-9]{3,}", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    bigrams = ["".join(cjk[index : index + 2]) for index in range(len(cjk) - 1)]
    return list(dict.fromkeys(latin + (bigrams if len(cjk) > 1 else cjk)))


def match_score(query: str, record: dict) -> float:
    """Fraction of query terms present in the record's title/authors/year."""
    terms = query_terms(query)
    if not terms:
        return 0.0
    haystack = " ".join(
        [str(record.get("title") or "")]
        + [str(author) for author in record.get("authors") or []]
        + [str(record.get("year") or "")]
    ).lower()
    hits = sum(1 for term in terms if term in haystack)
    return round(hits / len(terms), 3)


# --------------------------------------------------------------------------- #
# DSpace 7 (OAPEN / DOAB)
# --------------------------------------------------------------------------- #


def _dspace_item_record(item: dict, *, provider: str, base: str) -> dict:
    metadata = item.get("metadata") or {}

    def first(name: str) -> str | None:
        entries = metadata.get(name)
        if isinstance(entries, list) and entries:
            return _clean(entries[0].get("value"))
        return None

    def many(name: str) -> list[str]:
        entries = metadata.get(name)
        if not isinstance(entries, list):
            return []
        return [value for value in (_clean(e.get("value")) for e in entries) if value]

    title = _clean(item.get("name")) or first("dc.title")
    authors = many("dc.contributor.author") or many("dc.contributor.editor")
    language = first("dc.language.iso") or first("dc.language")
    handle = _clean(item.get("handle"))
    landing = first("dc.identifier.uri") or (
        f"https://hdl.handle.net/{handle}" if handle else None
    )
    identifiers = {}
    if handle:
        identifiers["handle"] = handle
    for isbn in many("dc.identifier.isbn"):
        identifiers.setdefault("isbn", []).append(isbn)
    doi = first("dc.identifier.doi")
    if doi:
        identifiers["doi"] = doi
    uuid = _clean(item.get("uuid"))
    if uuid:
        identifiers["dspace_uuid"] = uuid

    license_value = (
        first("dc.rights.uri")
        or first("dc.rights.license")
        or first("dc.rights")
        or first("oapen.rights.license")
    )
    return _record(
        source_provider=provider,
        title=title,
        authors=authors,
        year=_year_from(first("dc.date.issued") or first("dc.date.accessioned")),
        language=language,
        identifiers=identifiers,
        license=license_value,
        landing_url=landing,
        access_status=ACCESS_METADATA_ONLY,
        reason_not_evidence_eligible=_default_reason(ACCESS_METADATA_ONLY),
        provider_record={
            "dspace_uuid": uuid,
            "api_base": base,
            "abstract": first("dc.description.abstract"),
            "publisher": first("dc.publisher"),
        },
    )


def _dspace_search(base: str, *, provider: str, query: str, limit: int) -> list[dict]:
    payload = http_get_json(
        f"{base}/server/api/discover/search/objects",
        {"query": query, "size": limit, "dsoType": "item"},
    )
    objects = (
        (((payload or {}).get("_embedded") or {}).get("searchResult") or {})
        .get("_embedded", {})
        .get("objects", [])
    )
    records = []
    for entry in objects:
        item = (entry or {}).get("_embedded", {}).get("indexableObject")
        if isinstance(item, dict):
            records.append(_dspace_item_record(item, provider=provider, base=base))
    return records


def _dspace_bitstreams(item_uuid: str, base: str) -> list[dict]:
    """ORIGINAL-bundle bitstreams of one item (the actual downloadable files)."""
    payload = http_get_json(f"{base}/server/api/core/items/{item_uuid}/bundles")
    bundles = (payload or {}).get("_embedded", {}).get("bundles", [])
    collected: list[dict] = []
    for bundle in bundles:
        name = str(bundle.get("name") or "")
        if name not in {"ORIGINAL", "CONTENT"}:
            continue
        href = ((bundle.get("_links") or {}).get("bitstreams") or {}).get("href")
        if not href:
            continue
        bundle_payload = http_get_json(href)
        embedded = (bundle_payload or {}).get("_embedded", {}).get("bitstreams", [])
        for stream in embedded:
            content_href = ((stream.get("_links") or {}).get("content") or {}).get("href")
            collected.append(
                {
                    "name": _clean(stream.get("name")),
                    "size": stream.get("sizeBytes"),
                    "content_url": content_href,
                    "mimetype": (
                        (stream.get("metadata") or {}).get("dc.format.mimetype") or [{}]
                    )[0].get("value"),
                }
            )
    return collected


def _dspace_attach_pdf(records: list[dict], base: str) -> list[dict]:
    """Upgrade records that really carry an open PDF bitstream."""
    for record in records:
        uuid = record["provider_record"].get("dspace_uuid")
        if not uuid:
            continue
        try:
            streams = _dspace_bitstreams(uuid, base)
        except ProviderError as error:  # keep the metadata record, note the gap
            record["provider_record"]["bitstream_error"] = str(error)
            continue
        record["provider_record"]["bitstreams"] = streams
        pdfs = [
            stream
            for stream in streams
            if _is_pdf_url(stream.get("content_url"))
            or str(stream.get("mimetype") or "").lower() == "application/pdf"
        ]
        if pdfs:
            chosen = max(pdfs, key=lambda stream: stream.get("size") or 0)
            record["pdf_url"] = chosen.get("content_url")
            record["access_status"] = ACCESS_OPEN_PDF
            record["reason_not_evidence_eligible"] = None
        elif streams:
            record["access_status"] = ACCESS_OPEN_PAGE
            record["reason_not_evidence_eligible"] = (
                "open full text available, but no PDF bitstream (only "
                + ", ".join(sorted({str(s.get("name")) for s in streams}))
                + ")"
            )
        recompute_eligibility(record)
    return records


def search_oapen(query: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    return _dspace_attach_pdf(
        _dspace_search(OAPEN_BASE, provider="oapen", query=query, limit=limit),
        OAPEN_BASE,
    )


def search_doab(query: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    return _dspace_attach_pdf(
        _dspace_search(DOAB_BASE, provider="doab", query=query, limit=limit),
        DOAB_BASE,
    )


# --------------------------------------------------------------------------- #
# Google Books
# --------------------------------------------------------------------------- #


def search_google_books(query: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    # The API key is optional in Google's documentation, but the anonymous
    # shared-IP quota is exhausted almost immediately (observed HTTP 429
    # "Queries per day" on the very first call). If the operator supplies a
    # free key in GOOGLE_BOOKS_API_KEY it is used; this code never creates one.
    params = {
        "q": query,
        "maxResults": max(1, min(40, limit)),
        "printType": "books",
    }
    api_key = os.environ.get("GOOGLE_BOOKS_API_KEY")
    if api_key:
        params["key"] = api_key
    payload = http_get_json(
        GOOGLE_BOOKS_API,
        params,
    )
    records = []
    for item in (payload or {}).get("items", []):
        info = item.get("volumeInfo") or {}
        access = item.get("accessInfo") or {}
        pdf = access.get("pdf") or {}
        epub = access.get("epub") or {}
        identifiers = {}
        for entry in info.get("industryIdentifiers") or []:
            kind = str(entry.get("type") or "").lower()
            value = _clean(entry.get("identifier"))
            if value:
                identifiers.setdefault(kind, []).append(value)
        download_link = _clean(pdf.get("downloadLink"))
        public_domain = bool(access.get("publicDomain"))
        viewability = _clean(access.get("viewability"))
        if download_link:
            status = ACCESS_OPEN_PDF
            reason = None
        elif viewability == "ALL_PAGES" and public_domain:
            status = ACCESS_OPEN_PAGE
            reason = "full public-domain view but no direct PDF download link"
        elif viewability in {"PARTIAL", "ALL_PAGES"}:
            status = ACCESS_METADATA_ONLY
            reason = f"Google Books viewability={viewability} is a preview, not full text"
        else:
            status = ACCESS_METADATA_ONLY
            reason = _default_reason(ACCESS_METADATA_ONLY)
        records.append(
            _record(
                source_provider="google_books",
                title=_clean(info.get("title")),
                authors=[a for a in (info.get("authors") or []) if _clean(a)],
                year=_year_from(info.get("publishedDate")),
                language=_clean(info.get("language")),
                identifiers=identifiers,
                access_status=status,
                reason_not_evidence_eligible=reason,
                license="public domain (Google Books)" if public_domain else None,
                landing_url=_clean(info.get("infoLink"))
                or _clean(info.get("canonicalVolumeLink")),
                pdf_url=download_link,
                pdf_hint=(
                    None
                    if download_link
                    else _clean(pdf.get("acsTokenLink") or epub.get("acsTokenLink"))
                ),
                provider_record={
                    "volume_id": _clean(item.get("id")),
                    "viewability": viewability,
                    "embeddable": access.get("embeddable"),
                    "public_domain": public_domain,
                    "epub_available": bool(epub.get("isAvailable")),
                    "pdf_available": bool(pdf.get("isAvailable")),
                    "web_reader_link": _clean(access.get("webReaderLink")),
                    "publisher": _clean(info.get("publisher")),
                    "used_api_key": bool(api_key),
                },
            )
        )
    return records


# --------------------------------------------------------------------------- #
# OpenAlex (scholarly OA; Unpaywall's successor for free-text OA resolution)
# --------------------------------------------------------------------------- #


OPENALEX_OPEN_OA_STATUSES = {"gold", "green", "hybrid", "bronze"}


def _location_is_oa(location: dict | None) -> bool:
    """Does *this* location carry a clear open-access signal?

    OpenAlex marks access per location. A work can be ``is_oa:true`` overall
    while a particular ``pdf_url`` (e.g. a publisher mirror) sits on a location
    that is itself closed; the location flag — not the work flag — is what the
    download decision must rest on.
    """
    if not isinstance(location, dict):
        return False
    if location.get("is_oa") is True:
        return True
    return str(location.get("oa_status") or "").lower() in OPENALEX_OPEN_OA_STATUSES


def _best_open_location(work: dict) -> dict | None:
    """Prefer a location that is itself open; never promote a closed one.

    Order: OpenAlex's own ``best_oa_location`` when it is open and has a PDF →
    any open location with a PDF → any open location → ``best_oa_location`` →
    the first location (open or not, for metadata only).
    """
    locations = [
        location
        for location in (work.get("locations") or [])
        if isinstance(location, dict)
    ]
    best = work.get("best_oa_location")
    if isinstance(best, dict) and _location_is_oa(best) and _clean(best.get("pdf_url")):
        return best
    open_pdf = [
        location
        for location in locations
        if _location_is_oa(location) and _clean(location.get("pdf_url"))
    ]
    if open_pdf:
        return open_pdf[0]
    open_any = [location for location in locations if _location_is_oa(location)]
    if open_any:
        return open_any[0]
    if isinstance(best, dict):
        return best
    return locations[0] if locations else None


def search_openalex(query: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    payload = http_get_json(
        f"{OPENALEX_API}/works",
        {
            "search": query,
            "per-page": max(1, min(50, limit)),
            "filter": "is_oa:true",
        },
    )
    records = []
    for work in (payload or {}).get("results", []):
        location = _best_open_location(work)
        pdf_url = _clean((location or {}).get("pdf_url"))
        location_is_oa = _location_is_oa(location)
        landing_url = _clean((location or {}).get("landing_page_url")) or _clean(
            ((work.get("primary_location") or {}) or {}).get("landing_page_url")
        )
        location_license = _clean((location or {}).get("license"))
        license_value = location_license or _clean(
            ((work.get("primary_location") or {}) or {}).get("license")
        )
        oa_status = _clean(((work.get("open_access") or {}) or {}).get("oa_status"))
        location_oa_status = _clean((location or {}).get("oa_status"))
        if pdf_url and location_is_oa:
            status, reason = ACCESS_OPEN_PDF, None
        elif pdf_url:
            status = ACCESS_METADATA_ONLY
            reason = (
                "OpenAlex returned a PDF URL on a location that is not itself "
                "marked open access; refusing to auto-download it"
            )
        elif landing_url and location_is_oa:
            status = ACCESS_OPEN_PAGE
            reason = "open-access landing page, no direct PDF URL in OpenAlex"
        else:
            status = ACCESS_METADATA_ONLY
            reason = _default_reason(ACCESS_METADATA_ONLY)
        identifiers = {}
        doi = _clean(work.get("doi"))
        if doi:
            identifiers["doi"] = doi.replace("https://doi.org/", "")
        openalex_id = _clean(work.get("id"))
        if openalex_id:
            identifiers["openalex"] = openalex_id.rsplit("/", 1)[-1]
        records.append(
            _record(
                source_provider="openalex",
                title=_clean(work.get("title"))
                or _clean(work.get("display_name")),
                authors=[
                    _clean((entry.get("author") or {}).get("display_name"))
                    for entry in (work.get("authorships") or [])[:6]
                    if _clean((entry.get("author") or {}).get("display_name"))
                ],
                year=_year_from(work.get("publication_year")),
                language=_clean(work.get("language")),
                identifiers=identifiers,
                access_status=status,
                reason_not_evidence_eligible=reason,
                license=license_value,
                landing_url=landing_url,
                pdf_url=pdf_url,
                provider_record={
                    "type": _clean(work.get("type")),
                    "oa_status": oa_status,
                    "location_is_oa": location_is_oa,
                    "location_oa_status": location_oa_status,
                    "location_license": location_license,
                    "location_version": _clean((location or {}).get("version")),
                    "location_host": _clean(
                        ((location or {}).get("source") or {}).get("display_name")
                    ),
                    "is_retracted": work.get("is_retracted"),
                    "cited_by_count": work.get("cited_by_count"),
                },
            )
        )
    return records


# --------------------------------------------------------------------------- #
# Internet Archive (public-domain / open-download items only)
# --------------------------------------------------------------------------- #


# Collection membership is *not* a rights claim. Only Project Gutenberg is
# trusted on collection membership alone (its deposits are public domain by
# policy). Broad collections such as ``americana`` and the self-asserted
# ``opensource`` are deliberately NOT sufficient: an item in them must still
# carry an explicit rights / licence / public-domain signal. This is the
# control-room hardening requested before any durable adoption.
IA_COLLECTION_ONLY_TRUSTED = {"gutenberg"}
IA_BROAD_COLLECTIONS = {"americana", "opensource"}
IA_RESTRICTED_COLLECTIONS = {"inlibrary", "printdisabled", "lendinglibrary"}

# Explicit public-domain / no-known-copyright phrases as the archive writes
# them (``NOT_IN_COPYRIGHT`` vs ``not in copyright`` is normalised first).
IA_PUBLIC_DOMAIN_MARKERS = (
    "not in copyright",
    "no known copyright",
    "public domain",
    "publicdomain",
    "cc0",
    "creative commons zero",
)

# Explicit open-licence URLs that are an unambiguous rights statement on their
# own (Creative Commons licences / public-domain marks, Open Data Commons).
IA_OPEN_LICENSE_MARKERS = (
    "creativecommons.org/licenses/",
    "creativecommons.org/publicdomain/",
    "opendatacommons.org/licenses/",
    "open government licence",
)


def _ia_rights_text(metadata: dict) -> str:
    """Raw rights-bearing metadata, whatever its spelling."""
    return " ".join(
        str(metadata.get(key) or "")
        for key in ("rights", "licenseurl", "possible-copyright-status", "copyright")
    ).strip()


def _ia_explicit_open_signal(metadata: dict) -> tuple[bool, str | None]:
    """Is there an explicit rights/licence signal (independent of collection)?

    Returns ``(True, signal_text)`` when the archive's own metadata states a
    public-domain / no-known-copyright status or links an open licence, and
    ``(False, None)`` otherwise. Collection membership is *never* consulted
    here, so the caller can distinguish "explicitly open" from "open-looking".
    """
    raw = _ia_rights_text(metadata)
    if not raw:
        return False, None
    normalised = re.sub(r"[_\-]+", " ", raw).lower()
    for marker in IA_PUBLIC_DOMAIN_MARKERS:
        if marker in normalised:
            return True, f"rights text matches {marker!r}"
    lowered = raw.lower()
    for marker in IA_OPEN_LICENSE_MARKERS:
        if marker in lowered:
            return True, f"licence URL matches {marker!r}"
    return False, None


def _ia_is_open(metadata: dict, file_entry: dict) -> tuple[bool, str | None]:
    """Open-download decision from the archive's own access/licence signals.

    The archive reports the same concept under several field spellings
    (``NOT_IN_COPYRIGHT`` vs ``not in copyright``), so separators are
    normalised before matching. Any lending/restriction marker wins over an
    open-looking collection, because borrowing must never be automated.

    Hardened rule (control-room requested): an explicit public-domain / open
    licence signal is required for every item. Collection membership alone is
    trusted only for Project Gutenberg; the broad ``americana`` and
    ``opensource`` collections are no longer treated as a rights signal.
    """
    collection = metadata.get("collection") or []
    if isinstance(collection, str):
        collection = [collection]
    collection = [str(entry).lower() for entry in collection]

    if file_entry.get("private") is True:
        return False, "the archive flags this file private"
    if str(file_entry.get("access-restricted-item") or "").lower() == "true":
        return False, "the archive flags this file access-restricted"
    if metadata.get("access-restricted-item") is True:
        return False, "the archive flags this item access-restricted"
    if IA_RESTRICTED_COLLECTIONS & set(collection):
        return False, "lending/print-disabled item; borrowing is not automated"

    explicit, _signal = _ia_explicit_open_signal(metadata)
    if explicit:
        return True, None
    if IA_COLLECTION_ONLY_TRUSTED & set(collection):
        return True, None

    raw_rights = _ia_rights_text(metadata)
    broad = sorted(IA_BROAD_COLLECTIONS & set(collection))
    collection_note = (
        f"; collection membership {broad} is not on its own a rights signal"
        if broad
        else ""
    )
    return False, (
        "no explicit public-domain / open-licence signal"
        + collection_note
        + (f" (signals={raw_rights.strip()[:80]!r})" if raw_rights.strip() else "")
    )


def search_internet_archive(query: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    payload = http_get_json(
        INTERNET_ARCHIVE_SEARCH,
        {
            "q": f"({query}) AND mediatype:texts",
            "fl[]": [
                "identifier",
                "title",
                "creator",
                "year",
                "date",
                "language",
                "licenseurl",
                "collection",
            ],
            "rows": max(1, min(50, limit)),
            "page": 1,
            "output": "json",
        },
    )
    docs = (((payload or {}).get("response") or {}).get("docs")) or []
    records = []
    for doc in docs:
        identifier = _clean(doc.get("identifier"))
        if not identifier:
            continue
        try:
            metadata = http_get_json(f"{INTERNET_ARCHIVE_METADATA}/{identifier}")
        except ProviderError as error:
            records.append(
                _record(
                    source_provider="internet_archive",
                    title=_clean(doc.get("title")),
                    access_status=ACCESS_ERROR,
                    reason_not_evidence_eligible=str(error),
                    provider_record={"identifier": identifier},
                )
            )
            continue
        files = (metadata or {}).get("files") or []
        meta = (metadata or {}).get("metadata") or {}
        creator = _clean(doc.get("creator")) or _clean(meta.get("creator"))
        explicit_open, open_signal_text = _ia_explicit_open_signal(meta)
        candidates = []
        for entry in files:
            name = str(entry.get("name") or "")
            if not name.lower().endswith(".pdf"):
                continue
            open_ok, refusal = _ia_is_open(meta, entry)
            candidates.append((entry, open_ok, refusal, open_signal_text))
        open_pdfs = [entry for entry, ok, _, _ in candidates if ok]
        if open_pdfs:
            chosen = open_pdfs[0]
            status, reason = ACCESS_OPEN_PDF, None
        elif candidates:
            status = ACCESS_METADATA_ONLY
            reason = (
                "PDF exists but is not clearly open to download: "
                + (candidates[0][2] or "unclear archive rights")
            )
        else:
            status = ACCESS_METADATA_ONLY
            reason = "no PDF file in this archive item"
        record = _record(
            source_provider="internet_archive",
            title=_clean(doc.get("title")) or _clean(meta.get("title")),
            authors=[creator] if creator else [],
            year=_year_from(doc.get("year") or doc.get("date")),
            language=_clean(doc.get("language") or meta.get("language")),
            identifiers={"ia_identifier": identifier},
            access_status=status,
            reason_not_evidence_eligible=reason,
            license=_clean(meta.get("licenseurl")),
            landing_url=f"https://archive.org/details/{identifier}",
            pdf_url=(
                f"https://archive.org/download/{identifier}/"
                + urllib.parse.quote(str(chosen.get("name")))
                if open_pdfs
                else None
            ),
            provider_record={
                "identifier": identifier,
                "collection": meta.get("collection"),
                "explicit_rights_signal": explicit_open,
                "rights_signal_text": open_signal_text,
                "pdf_files": [
                    {
                        "name": entry.get("name"),
                        "size": entry.get("size"),
                        "open_signal": ok,
                        "refusal": refusal,
                        "rights_signal": signal_text,
                    }
                    for entry, ok, refusal, signal_text in candidates
                ],
            },
        )
        records.append(record)
    return records


# --------------------------------------------------------------------------- #
# Chinese Wikisource (open community transcription; a lead, never evidence)
# --------------------------------------------------------------------------- #


def search_wikisource(query: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Search the Chinese Wikisource MediaWiki API (free, no key, CC BY-SA).

    This is deliberately *not* evidence-eligible. Wikisource text is a
    community transcription hosted on a wiki: it has no fixed page images and
    no printed-page provenance, so it can only ever be a discovery lead. The
    page-grounded evidence contract is unchanged.
    """
    payload = http_get_json(
        WIKISOURCE_API,
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": max(1, min(20, limit)),
            "format": "json",
        },
    )
    hits = ((payload or {}).get("query") or {}).get("search") or []
    records = []
    for hit in hits:
        title = _clean(hit.get("title"))
        if not title:
            continue
        page_id = hit.get("pageid")
        records.append(
            _record(
                source_provider="wikisource_zh",
                title=title,
                language="zh",
                identifiers={"wikisource_pageid": page_id} if page_id else {},
                access_status=ACCESS_OPEN_PAGE,
                reason_not_evidence_eligible=(
                    "community transcription on a wiki (CC BY-SA), no fixed page "
                    "images; usable as a lead, not page-grounded primary evidence"
                ),
                license="CC BY-SA (community transcription)",
                landing_url="https://zh.wikisource.org/wiki/"
                + urllib.parse.quote(str(title).replace(" ", "_")),
                provider_record={
                    "namespace": hit.get("ns"),
                    "wordcount": hit.get("wordcount"),
                    "snippet": re.sub("<[^>]+>", "", str(hit.get("snippet") or "")),
                },
            )
        )
    return records


# --------------------------------------------------------------------------- #
# Aggregation + download
# --------------------------------------------------------------------------- #


PROVIDERS = {
    "oapen": search_oapen,
    "doab": search_doab,
    "google_books": search_google_books,
    "openalex": search_openalex,
    "internet_archive": search_internet_archive,
    "wikisource_zh": search_wikisource,
}

# Order matters: the product prefers genuinely open PDFs, so the two DSpace
# book repositories are asked first and the metadata-heavy sources last.
# OAPEN/DOAB currently answer HTTP 403 "You address is not allowed to access
# this API" from this environment, so they are queried but reported honestly
# rather than silently skipped.
DEFAULT_PROVIDER_ORDER = (
    "oapen",
    "doab",
    "openalex",
    "google_books",
    "internet_archive",
    "wikisource_zh",
)


def search_all(
    query: str,
    *,
    limit: int = DEFAULT_LIMIT,
    providers: tuple[str, ...] = DEFAULT_PROVIDER_ORDER,
) -> dict:
    query = (query or "").strip()
    if not query:
        raise ValueError("query is required")
    results: list[dict] = []
    report = []
    for name in providers:
        function = PROVIDERS.get(name)
        if function is None:
            report.append({"provider": name, "ok": False, "error": "unknown provider"})
            continue
        try:
            found = function(query, limit)
        except ProviderError as error:
            report.append(
                {
                    "provider": name,
                    "ok": False,
                    "error": str(error),
                    "status": error.status,
                }
            )
            continue
        except Exception as error:  # noqa: BLE001 - one provider must not kill the search
            report.append({"provider": name, "ok": False, "error": str(error)})
            continue
        for record in found:
            record["match_score"] = match_score(query, record)
        results.extend(found)
        report.append({"provider": name, "ok": True, "count": len(found)})
    results.sort(key=_rank)
    outcome = classify_outcome(results, report)
    return {
        "query": query,
        "providers": report,
        "outcome": outcome,
        "results": results,
        "relevance_floor": RELEVANCE_FLOOR,
    }


def _access_rank(record: dict) -> int:
    order = {
        ACCESS_OPEN_PDF: 0,
        ACCESS_OPEN_PAGE: 1,
        ACCESS_METADATA_ONLY: 2,
        ACCESS_ERROR: 3,
        ACCESS_RATE_LIMIT: 4,
    }
    return order.get(record.get("access_status"), 9)


def _rank(record: dict) -> tuple:
    """Most relevant first, then the most usable access status."""
    return (
        -float(record.get("match_score") or 0.0),
        _access_rank(record),
        str(record.get("title") or ""),
    )


def classify_outcome(results: list[dict], report: list[dict] | None = None) -> dict:
    """Honest top-level answer for one query.

    Only records above the (cheap, explainable) relevance floor can drive the
    answer, so an unrelated open PDF can never be announced as the user's
    source. The wording always says "candidate" — a human decides.
    """
    relevant = [
        record
        for record in results
        if float(record.get("match_score") or 0.0) >= RELEVANCE_FLOOR
    ]
    eligible = [r for r in relevant if r.get("evidence_eligible")]
    if eligible:
        return {
            "status": ACCESS_OPEN_PDF,
            "message": (
                f"发现 {len(eligible)} 个可直接下载的开放 PDF 候选，"
                "请人工确认是否就是你引用的文献，再交给核验流程。"
            ),
            "open_pdf_count": len(eligible),
        }
    open_pages = [r for r in relevant if r.get("access_status") == ACCESS_OPEN_PAGE]
    if open_pages:
        return {
            "status": ACCESS_OPEN_PAGE,
            "message": (
                "找到相关的开放全文（非 PDF），它只能当线索，"
                "不能作为页码可核验的一手证据；请上传你合法获得的 PDF。"
            ),
            "open_page_count": len(open_pages),
        }
    if relevant:
        return {
            "status": ACCESS_METADATA_ONLY,
            "message": (
                "只找到相关书目/预览信息，不能作为页码可核验的一手证据。"
                "请上传你合法获得的一手文献 PDF。"
            ),
            "metadata_count": len(relevant),
        }
    if report and all(not entry.get("ok") for entry in report):
        return {
            "status": ACCESS_ERROR,
            "message": "所有来源都无法查询（网络或限流），请稍后重试或直接上传 PDF。",
        }
    if results:
        return {
            "status": ACCESS_USER_UPLOAD,
            "message": (
                "只找到与查询弱相关的记录，没有可用作页码可核验证据的开放 PDF。"
                "请上传你合法获得的一手文献 PDF。"
            ),
            "weak_match_count": len(results),
        }
    return {
        "status": ACCESS_USER_UPLOAD,
        "message": "没有找到合法可下载的开放全文。请上传你合法获得的一手文献 PDF。",
    }


class DownloadRefused(RuntimeError):
    """The record is not allowed to be auto-downloaded."""


def download_open_pdf(
    record: dict,
    dest_dir: Path,
    *,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
    timeout: int = 120,
) -> dict:
    """Download a record's ``pdf_url`` iff it is openly and unambiguously open.

    Refuses anything that is not ``evidence_eligible``, validates the ``%PDF``
    header, and writes into ``dest_dir`` only. Returns the saved path plus the
    provenance that must travel with the file.
    """
    if not record.get("evidence_eligible"):
        raise DownloadRefused(
            "record is not evidence-eligible ("
            + str(record.get("reason_not_evidence_eligible"))
            + ")"
        )
    url = record.get("pdf_url")
    if not url:
        raise DownloadRefused("record has no pdf_url")
    if urllib.parse.urlparse(url).scheme not in {"http", "https"}:
        raise DownloadRefused(f"non-http pdf_url: {url!r}")
    dest_dir = Path(dest_dir).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            declared = int(response.headers.get("Content-Length") or 0)
            if declared and declared > max_bytes:
                raise DownloadRefused(
                    f"declared size {declared} exceeds limit {max_bytes}"
                )
            first = response.read(5)
            if not first.startswith(PDF_MAGIC):
                content_type = response.headers.get("Content-Type") or "unknown"
                raise DownloadRefused(
                    "response is not a PDF (no %PDF header; Content-Type="
                    f"{content_type}, starts with {first[:5]!r}); refusing to save"
                )
            suffix = ".pdf"
            stem = re.sub(r"[^A-Za-z0-9._-]+", "_", str(record.get("title") or "source"))
            target = dest_dir / (stem[:80].strip("._-") or "source")
            target = target.with_suffix(suffix)
            counter = 1
            while target.exists():
                target = target.with_name(f"{target.stem}-{counter}{suffix}")
                counter += 1
            with target.open("wb") as handle:
                handle.write(first)
                written = len(first)
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        handle.close()
                        target.unlink(missing_ok=True)
                        raise DownloadRefused(
                            f"download exceeded {max_bytes} bytes; removed partial file"
                        )
                    handle.write(chunk)
    except urllib.error.HTTPError as error:
        raise ProviderError(
            f"HTTP {error.code} downloading {url}",
            status=ACCESS_RATE_LIMIT if error.code == 429 else ACCESS_ERROR,
        ) from error
    except urllib.error.URLError as error:
        raise ProviderError(f"network error downloading {url}: {error.reason}") from error
    return {
        "path": str(target),
        "bytes": written,
        "source_provider": record.get("source_provider"),
        "landing_url": record.get("landing_url"),
        "pdf_url": url,
        "license": record.get("license"),
        "title": record.get("title"),
        "authors": record.get("authors"),
        "year": record.get("year"),
        "identifiers": record.get("identifiers"),
        "sha256": _sha256(target),
    }


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 256), b""):
            digest.update(block)
    return digest.hexdigest()


def write_provenance(saved: dict, path: Path) -> Path:
    """Persist the download provenance next to the file, never the bytes."""
    path = Path(path)
    path.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# CLI (live diagnostics; requires network)
# --------------------------------------------------------------------------- #


def _summarize(record: dict) -> str:
    authors = ", ".join(record.get("authors") or [])[:60]
    return (
        f"[{record.get('access_status'):<26}] m={float(record.get('match_score') or 0):.2f}"
        f" {record.get('source_provider'):<17}"
        f" | {str(record.get('title'))[:60]:<60} | {record.get('year') or '----'}"
        f" | {authors}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="query every provider and print a table")
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    search.add_argument("--json", action="store_true", help="dump the raw normalized JSON")
    search.add_argument(
        "--providers",
        default=",".join(DEFAULT_PROVIDER_ORDER),
        help="comma-separated provider subset",
    )

    probe = sub.add_parser("probe", help="dump raw provider payloads for shape inspection")
    probe.add_argument("--query", required=True)
    probe.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    probe.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    check = sub.add_parser("check", help="run the fixed live-check query set (network)")
    check.add_argument("--limit", type=int, default=3)
    check.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "probe":
        return _probe(args)
    if args.command == "check":
        return _check(args)
    return _search(args)


# Queries used for the live provider check in the Phase 1 report. They cover
# Chinese humanities metadata, a public-domain classic and an OA book query.
LIVE_CHECK_QUERIES = (
    "Plato Republic",
    "A Philosophy of Intellectual Property",
    "理想国 郭斌和 张竹明",
)


def _check(args) -> int:
    payload = []
    for query in LIVE_CHECK_QUERIES:
        print(f"== {query}")
        result = search_all(query, limit=args.limit)
        for entry in result["providers"]:
            if entry.get("ok"):
                print(f"   {entry['provider']:<17} ok  {entry['count']}")
            else:
                print(f"   {entry['provider']:<17} FAIL {entry.get('error')}")
        print(f"   outcome: {result['outcome']['status']}")
        for record in result["results"][:6]:
            print("   " + _summarize(record))
        payload.append(
            {
                "query": query,
                "providers": result["providers"],
                "outcome": result["outcome"],
                "results": result["results"],
            }
        )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _search(args) -> int:
    providers = tuple(p.strip() for p in args.providers.split(",") if p.strip())
    payload = search_all(args.query, limit=args.limit, providers=providers)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print(f"query: {payload['query']}")
    for entry in payload["providers"]:
        if entry.get("ok"):
            print(f"  {entry['provider']:<17} ok  {entry['count']} record(s)")
        else:
            print(f"  {entry['provider']:<17} FAIL {entry.get('error')}")
    print(f"outcome: {payload['outcome']['status']} — {payload['outcome']['message']}")
    for record in payload["results"]:
        print("  " + _summarize(record))
    return 0


def _probe(args) -> int:
    print(json.dumps(_raw_probe(args.provider, args.query, args.limit), ensure_ascii=False, indent=2))
    return 0


def _raw_probe(provider: str, query: str, limit: int):
    if provider == "google_books":
        return http_get_json(
            GOOGLE_BOOKS_API,
            {"q": query, "maxResults": limit, "printType": "books"},
        )
    if provider == "openalex":
        return http_get_json(
            f"{OPENALEX_API}/works",
            {"search": query, "per-page": limit, "filter": "is_oa:true"},
        )
    if provider in {"oapen", "doab"}:
        base = OAPEN_BASE if provider == "oapen" else DOAB_BASE
        return http_get_json(
            f"{base}/server/api/discover/search/objects",
            {"query": query, "size": limit, "dsoType": "item"},
        )
    if provider == "internet_archive":
        return http_get_json(
            INTERNET_ARCHIVE_SEARCH,
            {
                "q": f"({query}) AND mediatype:texts",
                "fl[]": ["identifier", "title", "year"],
                "rows": limit,
                "page": 1,
                "output": "json",
            },
        )
    if provider == "wikisource_zh":
        return http_get_json(
            WIKISOURCE_API,
            {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": limit,
                "format": "json",
            },
        )
    raise SystemExit(f"unknown provider {provider}")


if __name__ == "__main__":
    sys.exit(main())

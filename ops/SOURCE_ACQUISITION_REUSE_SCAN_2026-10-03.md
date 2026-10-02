# Source-acquisition Phase 1 — Reuse Scan (lawful / open discovery)

Status: COMPLETE. Bounded scan executed 2026-10-02 (Asia/Shanghai) during the
authorized overnight Goal `ops/SOURCE_ACQUISITION_OVERNIGHT_GOAL_2026-10-02.md`.

Scope: find the smallest set of *maintained, lawful, keyless* interfaces that can
answer one question — "the user has no primary PDF; is a genuinely open
full-text PDF available?" — and decide for each candidate: adopt, defer, or
reject. No paid service, no account, no API key, no borrowing, no paywall/DRM
bypass was used or created.

Every claim below was verified by a live request from the project machine on
2026-10-02, not from documentation alone. Raw evidence is in the benchmark
report and in `data/private/sa_benchmark/benchmark.json` (git-ignored).

## Decision summary

| Provider | Query capability | Full-text / PDF capability | Access signal | Automated download | Key / account | Chinese humanities value | Integration burden | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **OpenAlex** | free-text `search=` over works | `best_oa_location.pdf_url` / `locations[].pdf_url`; real PDFs for OA books and chapters | `open_access.oa_status`, per-location `license`, `is_oa` | yes when `pdf_url` really serves a PDF (must be header-checked) | none | medium (scholarly books/chapters; Chinese-language OA is thin) | low (one JSON call) | **ADOPT** |
| **Internet Archive** | `advancedsearch.php` fielded query + `metadata/<id>` | real scanned PDFs; some items add a `_text.pdf` derivative | `possible-copyright-status`, `rights`, `licenseurl`, `collection`, per-file `private` / `access-restricted-item` | yes **only** for explicitly public-domain/open items; lending items are refused in code | none | medium (PD Chinese books, `booksbylanguage_chinese`, 1930s–1980s Chinese periodicals) | medium (search + one metadata call per hit) | **ADOPT** |
| **Google Books** | `volumes?q=` with `intitle:`/`inauthor:`/ISBN | `accessInfo.pdf.downloadLink` for public-domain full view | `accessInfo.publicDomain`, `viewability`, `saleInfo` | yes when `downloadLink` exists (never observed in this environment) | anonymous quota failed; a **free** key is documented | high for bibliography, low for open full text | low (one JSON call) | **ADOPT but DEFERRED in practice** — see below |
| **OAPEN Library** | DSpace REST search | DSpace bitstream PDFs | `dc.rights*`, OAPEN licence metadata | intended yes; **not reachable from this machine** | none | low–medium (English/European OA books) | low once reachable | **DEFER (interface refused)** |
| **DOAB** | DSpace REST search | DSpace bitstream PDFs | `dc.rights*` | intended yes; **not reachable from this machine** | none | low–medium | low once reachable | **DEFER (interface refused)** |
| **中文维基文库 (Wikisource)** | MediaWiki `list=search` | open wiki text (HTML/wikitext), **no PDF** | CC BY-SA site licence | n/a (no file download) | none | high for classical Chinese texts | low (one JSON call) | **ADOPT as a lead only, never evidence** |
| **Unpaywall** | DOI resolution only (free-text search retired) | OA locations | `oa_status`, `license` | yes | requires an `email` parameter | low | low | **REJECT (superseded by OpenAlex)** |
| HathiTrust / Open Library / CORE / BASE | — | full text restricted, or requires a key/registration | — | no / gated | key or account | — | — | **REJECT (outside the keyless boundary)** |

Resulting preference: **direct reuse** of OpenAlex + Internet Archive for real
PDFs, **small adaptation** for Google Books and Wikisource, and **no custom
downloader/discovery engine** of our own.

## Exact interfaces verified

| Endpoint | Result on 2026-10-02 |
| --- | --- |
| `https://api.openalex.org/works?search=…&filter=is_oa:true` | 200 JSON; correct `best_oa_location.pdf_url` for OA books; occasional HTTP 429 under burst |
| `https://archive.org/advancedsearch.php?q=…&output=json` | 200 JSON (`response.docs`) |
| `https://archive.org/metadata/<identifier>` | 200 JSON (`metadata` + `files[]`) |
| `https://www.googleapis.com/books/v1/volumes?q=…` | **HTTP 429 on every call**, all retries: `Quota exceeded for quota metric 'Queries' and limit 'Queries per day' … consumer 'project_number:624717413613'` |
| `https://library.oapen.org/server/api/discover/search/objects` | HTTP 404 (HTML) |
| `https://library.oapen.org/rest/items`, `/rest/search` | HTTP 403 `You address is not allowed to access this API.` |
| `https://library.oapen.org/oai/request?verb=Identify` | 200 XML (OAI-PMH is reachable, but it is a harvesting protocol with no free-text search) |
| `https://directory.doabooks.org/…` | identical to OAPEN above |
| `https://zh.wikisource.org/w/api.php?action=query&list=search` | 200 JSON |
| `https://api.unpaywall.org/v2/<doi>?email=…` | not used: requires an email identifier and is superseded by OpenAlex |

## What is reusable

* **OpenAlex** replaces a scholarly-OA resolver entirely: one keyless call
  returns title, authors, year, DOI, OA status, licence and candidate PDF URLs.
  PaperQA2's own metadata path is not involved, so no new retrieval stack is
  needed.
* **Internet Archive** provides the page-grounded artifact the product actually
  needs — a scanned PDF with fixed page images — for public-domain material,
  including Chinese-language material.
* **Google Books** remains the best *bibliographic* disambiguator (editions,
  ISBN, translator) and, for public-domain titles, a documented PDF source.
* **Wikisource (zh)** is a free, keyless lead source for classical Chinese
  texts, which the two PDF-oriented providers cover poorly.
* The **product's existing evidence layer is reused unchanged**: a downloaded
  PDF is handed to `tools/mvp_pipeline.py` exactly like an uploaded one.

## What gap remains

* **No open PDF for in-copyright Chinese translations.** For the product's own
  core case (e.g. 柏拉图《理想国》郭斌和、张竹明译，商务印书馆 1986) every
  provider returns metadata or a borrowing-restricted record. The honest
  `USER_UPLOAD_REQUIRED` answer is the correct and only permitted outcome.
* **No keyless Chinese-language OA *book* repository** with a working search
  API was found. DOAB/OAPEN would be the closest fit but refuse this address;
  whether they answer from a normal user network is unverified.
* **Provider PDF URLs are claims, not guarantees.** Three of three OpenAlex
  `pdf_url` values for one query (Brill, OpenEdition, Durham) did not serve a
  PDF from this machine.
* **Relevance is not solved.** A bibliographic query can match unrelated open
  PDFs; the cheap term-overlap hint mitigates but does not solve this.

## Why custom code is still necessary

The custom surface is deliberately thin but not zero:

* no single existing service does *lawful discovery → open-PDF validation →
  page-grounded evidence* for Chinese humanities sources;
* the download guardrails (evidence-eligible only, http(s) only, `%PDF` header,
  size cap, git-ignored destination, provenance record) are product-specific
  evidence-integrity rules that no provider or library supplies;
* the relevance hint and the `USER_UPLOAD_REQUIRED` fallback encode this
  product's honesty contract.

That is ~600 lines of stdlib-only adapter code (`tools/source_acquisition.py`),
no new dependency, and no change to the accepted evidence layer.

## Reuse-first gate record

1. **Checked:** current repository (`tools/mvp_*`, no prior acquisition code);
   ChatGPT/Codex native capabilities (no source-acquisition connector);
   available Skills/Plugins/MCPs (no OA full-text connector for books); the six
   providers above; official API documentation behaviour, verified live.
2. **Reusable:** OpenAlex, Internet Archive, Google Books, Wikisource APIs; the
   existing `mvp_pipeline` evidence path; stdlib `urllib`/`http.server`.
3. **Gap:** lawful open PDFs for in-copyright Chinese humanities translations
   do not exist; provider PDF URLs need validation; relevance needs a human.
4. **Custom code still needed:** yes, but only the thin adapter + guardrails
   described above — no discovery engine, no downloader framework, no new
   parser, no new OCR, no new evidence layer.

# Source-acquisition Phase 1 — Report

Status: **COMPLETE** — post-MVP, experimental, reversible.

Run: 2026-10-02 (Asia/Shanghai), one continuous authorized overnight Goal
(`ops/SOURCE_ACQUISITION_OVERNIGHT_GOAL_2026-10-02.md`). Cost: **0 model calls,
$0.00**.

> Filename note: the brief names the two Phase 1 artifacts with a `2026-10-03`
> date for the morning handoff. The work actually executed and finished on
> 2026-10-02. Names follow the brief; timestamps inside are real.

## 1. What was asked, and what was delivered

Extend the accepted MVP in exactly one bounded direction: when the user has **no
primary-source PDF**, help find and lawfully acquire an open full-text PDF when
one genuinely exists — otherwise return an honest "upload your legally obtained
PDF" answer. The page-grounded evidence contract is unchanged, and no
unauthorized/pirated route was integrated.

Delivered:

* `tools/source_acquisition.py` — one normalized result schema and six thin
  provider adapters, stdlib-only, no new dependency, offline unless called.
* `tools/source_acquisition_probes.py` — **83/83** zero-cost offline probes.
* `tools/sa_benchmark.py` — the live 3-case benchmark + pipeline integration.
* A reversible route in `tools/mvp_app.py`: `③b 查找开放全文` → `/find` →
  `/use_found` → download → the **existing** confirm/run flow.
* One small hardening in `tools/mvp_pipeline.py` (see §7).

The uploaded-PDF path remains the primary, most reliable path and is untouched.

## 2. Providers checked (exact interfaces and boundary)

Full detail, including the reuse-first gate record: `ops/SOURCE_ACQUISITION_REUSE_SCAN_2026-10-03.md`.

| Provider | Official interface used | Live result | Decision |
| --- | --- | --- | --- |
| OpenAlex | `api.openalex.org/works?search=…&filter=is_oa:true` | works | ADOPT |
| Internet Archive | `archive.org/advancedsearch.php` + `/metadata/<id>` | works | ADOPT (public-domain only) |
| Google Books | `googleapis.com/books/v1/volumes` | HTTP 429, anonymous daily quota | ADOPT, unusable without a free key → **Human Gate** |
| OAPEN | DSpace 7 `/server/api/discover/search/objects`; DSpace 6 `/rest/*` | 404 (HTML) / 403 `You address is not allowed to access this API.` | DEFER (interface refused) |
| DOAB | same as OAPEN | 404 / 403 identical | DEFER (interface refused) |
| 中文维基文库 | `zh.wikisource.org/w/api.php` | works | ADOPT as a **lead only** |
| Unpaywall | `/v2/<doi>?email=` | not used: free-text search retired, email required, OpenAlex supersedes it | REJECT |

**Legal/access boundary enforced in code** — no bypass of any kind:

* only `http`/`https` URLs are ever fetched; `file://` and other schemes are
  refused;
* only records whose access status is `OPEN_PDF_AVAILABLE` **and** that carry a
  direct PDF URL may be downloaded (`evidence_eligible`);
* the response must start with `%PDF`; HTML/anti-bot/landing pages are refused
  and **nothing is written**;
* Internet Archive lending items (`inlibrary`/`printdisabled`), items with no
  explicit public-domain/open signal, files flagged `private` or
  `access-restricted-item`, are all refused with a recorded reason — borrowing
  is never automated;
* downloads land under the git-ignored `data/private/` tree only, with a
  `.provenance.json` recording provider, landing page, PDF URL, licence,
  byte count and sha256.

## 3. Adapters implemented

`tools/source_acquisition.py` (stdlib only — `urllib`, `json`, `re`, `time`).

Normalized record schema: `source_provider, title, authors, year, language,
identifiers, access_status, license, landing_url, pdf_url, pdf_hint,
evidence_eligible, reason_not_evidence_eligible, match_score, provider_record`.

Access states: `OPEN_PDF_AVAILABLE`, `OPEN_PAGE_SOURCE_AVAILABLE`,
`METADATA_OR_PREVIEW_ONLY`, `USER_UPLOAD_REQUIRED`, `ERROR`, `RATE_LIMIT`.

Two things worth calling out because they encode product honesty:

* **`evidence_eligible` requires both** the open-PDF status *and* a direct PDF
  URL. A status alone can never reach the evidence layer.
* **A cheap relevance hint** (fraction of query terms — Latin words plus CJK
  bigrams — found in title/authors) with a floor of `0.5` decides whether any
  open PDF may be *announced*. This exists because the first live run returned
  unrelated Chinese geoscience PDFs for the query `理想国 柏拉图`; without the
  floor the tool would have told the user "found an open PDF" for a book that
  has none. The hint is a ranking/announcement guard, never a correctness claim.

## 4. Benchmark evidence (live, 2026-10-02)

Command: `.venv\Scripts\python.exe tools\sa_benchmark.py --with-pipeline`
Report: `data/private/sa_benchmark/benchmark.json` (git-ignored).

| Case | Query | Outcome | Expected | Evidence-eligible | HTTP calls | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| `open_pd_book` | `The Republic Plato 1894` | `OPEN_PDF_AVAILABLE` | `OPEN_PDF_AVAILABLE` ✓ | 5 | 12 | 32.0 |
| `oa_scholarly_book` | `A Philosophy of Intellectual Property` | `OPEN_PDF_AVAILABLE` | `OPEN_PDF_AVAILABLE` ✓ | 3 | 12 | 20.4 |
| `closed_translation` | `理想国 郭斌和 张竹明` | `USER_UPLOAD_REQUIRED` | `USER_UPLOAD_REQUIRED` ✓ | 4 (all weak, `match_score` < 0.5) | 9 | 14.3 |

**A lawful open PDF was downloaded and verified, twice:**

* Internet Archive public-domain scan — *Plato's Republic: the Greek text*,
  `archive.org/download/afx0245.0003.001.umich.edu/…pdf`, **33,487,839 bytes,
  524 pages**, sha256 `e2d45f730112bc90eaf0a82f5a31e68ea2e3106cc9a0c15ff100666189668137`,
  `%PDF` header verified.
* OpenAlex OA book — *A Philosophy of Intellectual Property* (ANU Press),
  `press-files.anu.edu.au/downloads/press/n1902/pdf/book.pdf`, **1,275,990 bytes,
  312 pages**, sha256 `4df2c54961dadd4ccf541d39c3d798b9be57d95cc0cebd0e45359ddf9342d284`,
  `%PDF` header verified.

**False-positive / preview-only handling:** the third case returned four
"open PDF" records with zero term overlap plus one preview record at
`match_score 0.25`; the product answered `USER_UPLOAD_REQUIRED` instead of
announcing a match. Internet Archive lending items were refused with recorded
reasons across `红楼梦`, `四書 朱熹` and `论语` queries.

**Timing/cost:** 9–12 HTTP requests and 14–32 s per search (Google Books
contributes 3 wasted attempts through its retry ladder while rate-limited).
**0 model calls, $0.00.**

## 5. Did an acquired PDF enter the evidence pipeline?

**Yes, unchanged.** The smallest acquired PDF (312-page ANU OA book) was fed
through `tools/mvp_pipeline.py` exactly as an uploaded file would be:

| route | pages | chunks | candidates | located | highlight images | model calls | cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `text_layer` | 312 | 2466 | 5 | 4 | 6 | 0 | $0.00 |

Result state `multiple_candidates`; the secondary text used was a real 220-char
sentence read out of the acquired PDF, so this proves acquisition → parse →
chunk → local retrieval → T003 geometry → highlighted original page, with the
T003/T004 evidence rules intact and **no forked evidence layer**.

## 6. Failures, rate limits and honest limitations

* **OpenAlex `pdf_url` is a claim, not a guarantee.** For `Plato Republic` all
  three eligible candidates failed: Brill returned `Content-Type: text/html`
  with an empty body (anti-bot), OpenEdition returned HTTP 502, Durham
  repository returned HTTP 403. The `%PDF` guard refused all three and saved
  nothing. Reported per attempt in the benchmark JSON.
* **Google Books anonymous quota is exhausted** (`Queries per day` for the
  shared anonymous project). Every call 429s even after retries. The adapter
  supports `GOOGLE_BOOKS_API_KEY` but **no key was created** — that is a
  credential and therefore a Human Gate.
* **OAPEN/DOAB refuse this machine** (403 `You address is not allowed to access
  this API.` on their DSpace REST endpoints; 404 on the DSpace 7 path). Their
  OAI-PMH endpoint answers, but OAI-PMH is a bulk-harvest protocol with no
  free-text search, so integrating it would mean indexing an ~80k-record
  catalogue — far beyond a thin adapter. Recorded as DEFER rather than guessed
  at.
* **No relevance guarantee.** Term overlap cannot tell a translation from a
  commentary, and cannot see the translator. A human still confirms the
  candidate is the right work — the UI says "候选" for this reason.
* **Wikisource is a community transcription.** It is labelled non-evidence in
  code: no fixed page images, no printed-page provenance.
* **Not implemented:** printed-page mapping, OCR-accuracy certification,
  multi-edition comparison, any deployment/account work — all remain
  user-deferred post-MVP backlog.

## 7. Code changes

| File | Change |
| --- | --- |
| `tools/source_acquisition.py` | NEW — schema, 6 adapters, relevance hint, download guardrails, provenance, CLI (`search`/`probe`/`check`) |
| `tools/source_acquisition_probes.py` | NEW — 83 offline zero-cost probes |
| `tools/sa_benchmark.py` | NEW — live 3-case benchmark + pipeline integration check |
| `tools/mvp_app.py` | `③b 查找开放全文` card, `/find` and `/use_found` routes, `render_finder`, honest privacy text |
| `tools/mvp_pipeline.py` | one-line hardening: a caller supplying `metadata` as a dict no longer needs to know about optional `ocr_cache`/`citation`/`notes` keys |

No existing product code was deleted or replaced; no default path changed; no
dependency added (`requirements.txt` untouched — stdlib only).

## 8. Verification

| Suite | Result |
| --- | --- |
| `tools/mvp_probes.py` | **70/70** |
| `tools/t003_regression_probes.py` | **15/15** |
| `tools/t004_regression_probes.py` | **16/16** |
| `tools/t006_ocr_probes.py` | **5/5** |
| `tools/source_acquisition_probes.py` (new) | **83/83** |

All zero-cost: no model call, no paid API. `git ls-files data/private` is empty;
downloaded PDFs and provenance live only under the git-ignored
`data/private/sa_benchmark/`.

## 9. How to use it

Web surface (unchanged command, new section):

```
$env:PQA_HOME=$PWD; .\.venv\Scripts\python.exe tools\mvp_app.py
# http://127.0.0.1:8765  -> ③b 查找开放全文
```

CLI diagnostics:

```
.\.venv\Scripts\python.exe tools\source_acquisition.py search --query "Plato Republic"
.\.venv\Scripts\python.exe tools\source_acquisition.py check          # fixed 3-query live check
.\.venv\Scripts\python.exe tools\source_acquisition_probes.py         # offline, 83/83
.\.venv\Scripts\python.exe tools\sa_benchmark.py --with-pipeline      # live benchmark
```

## 10. Commits

| Commit | Purpose |
| --- | --- |
| _recorded in the follow-up state commit_ | Phase 1 implementation, reports and state update |

## 11. Recommended NEXT

**One recommendation:** resolve the two **Human Gates** that block any further
value here, before writing more code —

1. **Decide on a Google Books API key** (free, but it is a credential, so it
   needs your explicit approval). Without it, the strongest bibliographic
   disambiguator in the set is dead weight in every search.
2. **Decide the OAPEN/DOAB question**: their DSpace REST refuses this machine
   with 403 while OAI-PMH answers. Either you confirm they work from your own
   network (in which case the existing adapter is already correct and simply
   needs re-running), or the OA-book route stays closed and the honest
   `USER_UPLOAD_REQUIRED` answer is the product's final behaviour for
   in-copyright Chinese humanities translations.

Everything else in Phase 1 is finished, tested and reversible; nothing here
should be treated as durable architecture until you confirm it.

# Source-acquisition guardrail hardening — patch report

Status: **COMPLETE** — post-MVP, experimental, reversible. Cost this run:
**0 model calls, $0.00**.

Authorizing brief: `ops/SOURCE_ACQUISITION_GUARDRAIL_PATCH_GOAL_2026-10-03.md`
(control-room, D018 long-Goal routing). Executed: 2026-10-03 (Asia/Shanghai).

## 1. What was asked, and what was delivered

Phase 1 passed as experimental, with two conditions before durable adoption:
stop trusting broad Internet Archive collection membership as an open-rights
signal, and require the selected OpenAlex PDF location itself to carry an OA
signal. Both are now enforced in `tools/source_acquisition.py` and covered by
offline probes. No provider was added, no credential created, no paid call
made, and the primary-PDF upload path is untouched.

## 2. Internet Archive — explicit rights signal required

**Before:** `IA_OPEN_COLLECTIONS = {"gutenberg", "opensource", "americana"}` —
membership in any of the three was, on its own, treated as an open-rights
signal.

**After:** only `gutenberg` is trusted on collection membership alone. Every
other item — including the broad `americana` and the self-asserted
`opensource` — must carry an explicit rights / licence / public-domain signal:

- a public-domain / no-known-copyright phrase in `rights`,
  `possible-copyright-status`, `licenseurl` or `copyright`
  (`NOT_IN_COPYRIGHT`, `no known copyright`, `public domain`, `CC0`, …);
- or an explicit open-licence URL (`creativecommons.org/licenses/…`,
  `creativecommons.org/publicdomain/…`, `opendatacommons.org/licenses/…`).

Lending/print-disabled/private/access-restricted markers still win over
everything (borrowing is never automated). The refusal now names the reason,
e.g. *"no explicit public-domain / open-licence signal; collection membership
['americana'] is not on its own a rights signal"*, and the record carries
`explicit_rights_signal` / `rights_signal_text` for inspection.

**This is a real behaviour change, and it was verified live.** The item
downloaded during Phase 1 — Internet Archive `afx0245.0003.001.umich.edu`
(*Plato's Republic: the Greek text*, 1894, the 524-page scan) — lives in
`["michigan_books", "americana"]` and carries **no** rights field, so under the
hardened rule it is now **refused** (`METADATA_OR_PREVIEW_ONLY`) instead of
auto-downloaded. Its sibling Google-digitised scans
(`platosrepublicg00campgoog`) do carry `possible-copyright-status:
NOT_IN_COPYRIGHT` and are still recognised as explicitly open on the rights
axis (they expose no item-level PDF file, so they stay metadata-only anyway).

This is the intended trade-off: the 1894 scan is public domain by publication
date, but the archive does not assert it for that item, and the product must not
infer a licence from collection membership. The previously downloaded file
remains a valid Phase-1 artifact; the finder simply no longer auto-fetches it.

## 3. OpenAlex — the PDF location must itself be open

**Before:** any work matching `filter=is_oa:true` whose *best* location (or any
location, via a fallback) carried a `pdf_url` became evidence-eligible, so a
`pdf_url` sitting on a location that was not itself marked OA could be
auto-downloaded.

**After:** `_location_is_oa()` decides per location (`is_oa: true`, or an
explicit OpenAlex `oa_status` of `gold`/`green`/`hybrid`/`bronze`), and
`_best_open_location()` never promotes a closed location over an open one. A
`pdf_url` on a location without an OA signal is downgraded to
`METADATA_OR_PREVIEW_ONLY` with the reason *"OpenAlex returned a PDF URL on a
location that is not itself marked open access; refusing to auto-download
it"*. Each record now also stores `location_is_oa`, `location_oa_status`,
`location_license`, `location_version` and `location_host` for auditability.

A licence is preferred but not required: an otherwise-open location with no
licence name is still eligible, because `is_oa` is the access signal.

## 4. Offline verification (0 model calls, $0.00)

New probes (`tools/source_acquisition_probes.py`, all offline, no network):

- IA: explicit signal accepted (rights text, CC URL, CC0 URL, Gutenberg);
  `americana` alone, `opensource` alone, and the real
  `["michigan_books", "americana"]` no-rights shape refused; the old broad
  constant `IA_OPEN_COLLECTIONS` is asserted gone and
  `IA_COLLECTION_ONLY_TRUSTED == {"gutenberg"}`;
- OpenAlex: a `pdf_url` on a closed location is not evidence-eligible and is
  downgraded with an explanatory reason; an open, unlicensed location stays
  eligible; per-location OA flag and host are recorded.

| Suite | Before | After |
| --- | --- | --- |
| `tools/mvp_probes.py` | 70/70 | **70/70** |
| `tools/t003_regression_probes.py` | 15/15 | **15/15** |
| `tools/t004_regression_probes.py` | 16/16 | **16/16** |
| `tools/t006_ocr_probes.py` | 5/5 | **5/5** |
| `tools/source_acquisition_probes.py` | 83/83 | **98/98** |

## 5. Live re-check (network, 0 model calls, $0.00)

**Fixed three-query check** (`source_acquisition.py check --limit 3`):

| Query | Outcome | Note |
| --- | --- | --- |
| `Plato Republic` | `OPEN_PDF_AVAILABLE` | eligible candidates are OpenAlex OA PDFs; the IA scan is now metadata-only |
| `A Philosophy of Intellectual Property` | `OPEN_PDF_AVAILABLE` | OpenAlex OA book |
| `理想国 郭斌和 张竹明` | `USER_UPLOAD_REQUIRED` | only weak matches; honest refusal |

**Hardened live benchmark** (`sa_benchmark.py --out-dir
data/private/sa_benchmark_guardrail --with-pipeline`) — run in a separate
git-ignored directory so the Phase-1 evidence is preserved:

| Case | Outcome | Expected | Match |
| --- | --- | --- | --- |
| `open_pd_book` | `OPEN_PDF_AVAILABLE` | `OPEN_PDF_AVAILABLE` | ✓ |
| `oa_scholarly_book` | `OPEN_PDF_AVAILABLE` | `OPEN_PDF_AVAILABLE` | ✓ |
| `closed_translation` | `USER_UPLOAD_REQUIRED` | `USER_UPLOAD_REQUIRED` | ✓ |

- A real lawful OA PDF was still downloaded and validated under the hardened
  rule: ANU Press *A Philosophy of Intellectual Property*, 312 pages,
  1,275,990 bytes, sha256
  `4df2c54961dadd4ccf541d39c3d798b9be57d95cc0cebd0e45359ddf9342d284` —
  **byte-identical** to the Phase-1 download, confirming the tightening does
  not disturb the OA-book route.
- That acquired PDF ran through the **unchanged** canonical pipeline:
  `text_layer`, 312 pages, 2466 chunks, 5 candidates, 4 located, 6 highlighted
  original pages, `multiple_candidates`, **0 model calls / $0.00**.
- Honest residual: `open_pd_book` still downloads nothing, because all three
  eligible OpenAlex `pdf_url`s are refuted by the `%PDF` header guard
  (Brill → HTML, etc.). This is the Phase-1 finding, unchanged and reported,
  not a regression.

One transient was observed and is recorded rather than hidden: OpenAlex
returned HTTP 429 *"Anonymous search is temporarily rate-limited … retry in
13s"* on the first benchmark attempt, so `oa_scholarly_book` briefly reported
`METADATA_OR_PREVIEW_ONLY`. The retry ladder (1.5s, 4.0s) is shorter than that
window; a second run after the window passed every case. Honouring a longer
`Retry-After` is **not** part of this patch and is left as an observation.

## 6. Code changes

| File | Change |
| --- | --- |
| `tools/source_acquisition.py` | IA: `IA_COLLECTION_ONLY_TRUSTED` (Gutenberg only) + `_ia_explicit_open_signal()`; OpenAlex: `_location_is_oa()`, hardened `_best_open_location()`, per-location OA/eligibility decision and audit fields |
| `tools/source_acquisition_probes.py` | new IA rights-hardening probes + `probe_openalex_location_guard()` (83 → 98 checks) |
| `ops/SOURCE_ACQUISITION_GUARDRAIL_PATCH_GOAL_2026-10-03.md` | the control-room authorizing brief (already on `main`) |
| `ops/SOURCE_ACQUISITION_GUARDRAIL_PATCH_REPORT_2026-10-03.md` | this report (new) |
| `AGENTS.md`, `ops/PROJECT_STATE.md`, `ops/TASK_QUEUE.md`, `ops/RUN_LOG.md`, `ops/DECISIONS.md` | state-bus updates |

No dependency change (`requirements.txt` untouched); no default path changed;
the uploaded-PDF route remains primary.

## 7. Recommended NEXT

The two authorized hardening items are done. The remaining Phase-1 NEXT is a
**Human Gate**, not more engineering:

1. **Guarded real pilot** — run the accepted MVP + hardened finder on the
   user's own literature-tracing tasks and record value/failure evidence.
2. Deferred decisions still open: free Google Books API key or accept the
   anonymous-quota block; confirm whether OAPEN/DOAB answer from the user's own
   network; confirm whether the experimental finder is kept.

Durable adoption of the finder remains a Human Gate. No Google Books key was
created and no provider integration was broadened, per the authorizing scope.

# REPORT — Footnote-first V0.2 final browser-flow acceptance fixes — 2026-10-03

Status: **ACCEPTED / PASS** (D018 bounded defect-fix batch; control-room re-review completed 2026-10-03).

> Control-room acceptance: commit `ecbd2c9fbbab16c3da9fa230a8b316e5329f2a53`
> satisfies P0-F/P0-G/P0-H by code-level review. The rendered no-PDF path now
> exposes a real multipart PDF upload, blank identity edits remain cleared, and
> direct owned-PDF upload submits the current edited identity. The 7 new
> browser-path probes directly cover the three prior gaps. No GitHub Actions or
> commit-status checks exist for this commit, so the recorded suite counts remain
> Codex local execution evidence rather than an independent CI rerun. This is
> accepted as **pilot-ready**, not production-ready.

Goal: `ops/FOOTNOTE_FIRST_FINAL_ACCEPTANCE_FIX_GOAL_2026-10-03.md`.
Baseline fix commit: `0f5b30e`.
Authoritative product definition: `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md` (D022, D023).
Prior report: `ops/FOOTNOTE_FIRST_ACCEPTANCE_FIX_REPORT_2026-10-03.md`.

This is the second bounded acceptance patch to the V0.2 surface. No new provider,
credential, account, paid service, dependency, model call, RAG/evidence stack or
product scope was added. The canonical PDF evidence/highlight pipeline and the
source-acquisition guardrails are unchanged.

## Outcome in one line

The advertised workflow now works as a rendered browser path, not just as a
hand-built POST: the no-PDF page exposes a real owned-PDF upload, an
intentionally-cleared identity field stays cleared instead of being reparsed, and
edits made on the identification screen survive the direct owned-PDF upload into
the final bibliographic metadata and citation.

## What changed

### P0-F — the no-PDF result page now renders a usable owned-PDF upload

- `render_finder` replaces the non-multipart "return" form with a real
  `multipart/form-data` form posting to `/extract`, containing an
  `input[type=file][name=primary_file]` and carrying `secondary_text`,
  `footnote` and the confirmed `identity_json`. The "查找这一版" bundle is kept.
- The route still never calls `sa.search_all`: the owned-PDF continuation is
  offline with respect to source acquisition.

### P0-G — a cleared parsed identity field stays cleared

- `mvp_app.Handler._id_overrides` now returns every `id_*` field that is
  *present in the request* (blanks included) and `None` only when the request
  carries no `id_*` fields at all, distinguishing "absent" from "intentionally
  blank".
- `footnote_parse.build_identity` honours a blank override: it clears the field
  (never reselecting the parsed value), records
  `用户确认：留空（未识别）` provenance, adds the field to `unresolved`, and drops
  the parsed title variants so a cleared title is not re-offered for search.
  Because the citation composer only reads fields that survived, a cleared field
  also cannot reappear in the citation metadata.

### P0-H — identity-screen edits survive the direct owned-PDF upload

- `render_identity` folds the direct upload into the **same** `multipart` form as
  the editable `id_*` fields: the find button posts to `/find`, and the upload
  button uses `formaction='/extract'`, so the browser submits the current edits
  (including intentional blanks) together with the PDF.
- `mvp_app.Handler._carried_identity` builds the identity from posted `id_*`
  fields when present (edited values win, blanks clear), falling back to the
  serialised `identity_json` for later continuations and to `None` for the plain
  main-form upload. `/extract` therefore persists the edited identity into the
  confirmation step and, through it, into `/run`.

## Acceptance probes (`tools/footnote_first_probes.py`, 31 -> 38)

New rendered-browser-path checks that fail on `0f5b30e`:

| # | Probe | Requirement |
| --- | --- | --- |
| 19 | `no-pdf-page-renders-pdf-upload`, `rendered-upload-reaches-run-without-search` | no-PDF page exposes a real multipart `primary_file` control; the rendered path reaches `/run` with the confirmed identity and no second `sa.search_all` |
| 20 | `cleared-field-not-reparsed`, `cleared-field-respected-downstream` | a populated field blanked on the confirmation form stays blank in the search query, the echoed identity and the citation metadata |
| 21 | `identity-screen-in-form-upload`, `direct-upload-keeps-edited-identity`, `direct-upload-citation-uses-edits` | the in-form direct upload submits current edits (not the parse) into the final metadata/citation, offline |

## Tests / regressions (0 model calls, $0.00)

| Suite | Result |
| --- | --- |
| `tools/mvp_probes.py` | 70/70 |
| `tools/t003_regression_probes.py` | 15/15 |
| `tools/t004_regression_probes.py` | 16/16 |
| `tools/t006_ocr_probes.py` | 5/5 |
| `tools/source_acquisition_probes.py` | 98/98 |
| `tools/footnote_first_probes.py` | **38/38** |

The single-network-call invariant is preserved: `mvp_app.py` still contains
exactly one `sa.search_all(` call (reachable only from `POST /find`), and
`mvp_pipeline.py` still never imports the finder.

## Constraints honoured

- no new provider, credential, account, paid service or model call;
- no new dependency (stdlib-only changes);
- no new RAG/evidence stack; the accepted evidence/highlight pipeline is reused;
- no unauthorized/pirated acquisition; no broad scraping; guardrails intact;
- normal UI stays simple; D019/D022/D023 and the superseded v2 Goal untouched.

## Human gates

None triggered.

## NEXT

Begin a guarded real-user pilot on the user's own literature-tracing tasks using
the Footnote-first V0.2 surface. Record value, failure, and friction evidence
before any new provider, credential, resolver, or architecture expansion.

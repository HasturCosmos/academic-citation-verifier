# REPORT — Footnote-first V0.2 acceptance fixes — 2026-10-03

Status: COMPLETE (D018 bounded defect-fix batch). Control-room re-review: **FIX REQUIRED**.

> Re-review addendum (2026-10-03): commit `0f5b30e` materially closes the
> original four defects, but three browser-level continuity gaps remain: the
> no-PDF page does not render the promised PDF upload control, intentionally
> blank identity edits are reparsed back into old values, and direct owned-PDF
> upload from the editable identity screen loses current edits. Follow-up:
> `ops/FOOTNOTE_FIRST_FINAL_ACCEPTANCE_FIX_GOAL_2026-10-03.md`.
>
> Second-fix addendum (2026-10-03): those three browser-flow gaps are now
> **COMPLETE** — see `ops/FOOTNOTE_FIRST_FINAL_ACCEPTANCE_FIX_REPORT_2026-10-03.md`
> (`footnote_first_probes` 31 -> 38).

Goal: `ops/FOOTNOTE_FIRST_ACCEPTANCE_FIX_GOAL_2026-10-03.md`.
Baseline implementation: commit `9c929012`.
Authoritative product definition: `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md` (D022, D023).

This is a bounded acceptance patch to the V0.2 surface. No new provider,
credential, account, paid service, dependency, model call, RAG/evidence stack or
product scope was added. The canonical PDF evidence/highlight pipeline and the
source-acquisition guardrails are unchanged.

## Outcome in one line

The advertised three-block workflow is now a continuous, stateful path: the
secondary screenshot/PDF and the footnote screenshot are consumed on both the
identify path and the owned-PDF path, the user-confirmed bibliographic identity
survives every continuation and honestly feeds the citation metadata, the
insufficient-clue page really accepts a new clue, and the targeted lookup
prefers the confirmed Chinese-publication clues.

## What changed

### P0-A — `/identify` now ingests the secondary screenshot/PDF (`tools/mvp_app.py`)

- New shared helper `extract_uploaded_text(...)` reuses the existing
  text-layer / RapidOCR reader (no new OCR subsystem). `_handle_identify` now
  reads `secondary_file` as well as `footnote_file`; an attached file wins over
  an empty textarea. The extracted secondary text is carried through the hidden
  `secondary_text` field into `/find -> /use_found or /extract -> /run`.

### P0-B — the owned-PDF `/extract` path now ingests the footnote screenshot

- `_handle_extract` reads `footnote_file` with the same helper and puts the OCRed
  note into the confirmation form, so the main navigation clue is no longer lost
  on the direct-PDF route. `sa.search_all` is still never called on this route.

### P0-C — confirmed bibliographic identity survives continuation and feeds citations

- The smallest local state representation is the serialised confirmed identity:
  `_identity_hidden(prefill)` embeds it as a hidden `identity_json` field on the
  identity page's upload form, the finder records, the no-PDF upload form, the
  re-find form and the confirm form; `identity_json_field(...)` reads it back.
  `_handle_use_found` recovers it from the stored finder payload.
- `tools/footnote_parse.py` gained `identity_citation_metadata(identity)` and
  `compose_citation_metadata(source_metadata, identity)`. The Chinese containing
  publication is preferred over the cited work; the user-confirmed field wins,
  every difference from the PDF's own record is recorded in `metadata_conflicts`
  instead of being silently overwritten, and per-field provenance is recorded in
  `metadata_provenance`.
- Honesty rule: an original-language note with no Chinese-edition signal does not
  set `title`, so `t004.build_citations` returns no citation rather than dressing
  a foreign edition up as a Chinese one (`chinese_edition_confirmed=False`); with
  no identity at all the flag is `None` and no warning is shown.
- `tools/mvp_pipeline.py#run_pipeline(..., confirmed_identity=...)` composes that
  metadata and `build_evidence_objects` stamps the provenance/conflicts onto each
  product object; the result page renders the per-field sources and any conflict.

### P1-D — the "还需要一点脚注线索" page accepts a real new clue

- `render_ask_more_clue` now provides an editable footnote textarea, a footnote
  screenshot upload, and an owned-PDF upload form. No broad search is triggered
  while clues are insufficient.

### P1-E — targeted lookup prefers the confirmed publication

- `identity_queries` now puts a publication-oriented query first when a Chinese
  container / translator / publisher is confirmed (e.g. `社会科学方法论 韩水法 2013`),
  instead of discarding it behind a generic original-work query. Provider
  coverage and access guardrails are unchanged.

## Acceptance probes (`tools/footnote_first_probes.py`, 16 -> 31)

New real HTTP-path checks that fail on `9c929012`:

| # | Probe | Requirement |
| --- | --- | --- |
| 11 | `identify-reads-secondary-upload`, `identify-reads-footnote-upload` | secondary screenshot + footnote screenshot -> `/identify`: both survive |
| 12 | `extract-reads-footnote-screenshot`, `owned-pdf-run-keeps-note-no-search` | owned PDF + footnote screenshot -> `/extract`/`/run`: note survives, no search |
| 13 | `find-no-pdf-carries-identity`, `owned-pdf-continuation-keeps-edited-identity` | edited identity -> `/find` no PDF -> upload -> `/run`: survives |
| 14 | `find-open-pdf-carries-identity`, `use-found-run-keeps-edited-identity` | edited identity -> `/use_found` -> `/run`: survives |
| 15 | `confirmed-fields-produce-honest-citation` | confirmed fields -> citation strings + recorded provenance |
| 16 | `foreign-note-no-fabricated-chinese-citation` | foreign note, no Chinese-edition metadata -> no citation |
| 17 | `need-more-clue-editable`, `need-more-clue-retry-accepts-new-clue` | the retry page accepts an actual new clue |
| 18 | `single-targeted-network-call`, `evidence-routes-intact` | bounded network + accepted evidence routes unchanged |
| 4b | `lookup-prefers-confirmed-publication` | targeted query prefers the confirmed publication |

## Tests / regressions (0 model calls, $0.00)

| Suite | Result |
| --- | --- |
| `tools/mvp_probes.py` | 70/70 |
| `tools/t003_regression_probes.py` | 15/15 |
| `tools/t004_regression_probes.py` | 16/16 |
| `tools/t006_ocr_probes.py` | 5/5 |
| `tools/source_acquisition_probes.py` | 98/98 |
| `tools/footnote_first_probes.py` | **31/31** |

The single-network-call invariant is preserved: `mvp_app.py` still contains
exactly one `sa.search_all(` call (reachable only from `POST /find`), and
`mvp_pipeline.py` still never imports the finder.

## Constraints honoured

- no new provider, credential, account, paid service or model call;
- no new dependency (stdlib-only additions);
- no new RAG/evidence stack; the accepted PDF evidence/highlight pipeline is
  reused unchanged;
- no unauthorized/pirated acquisition; no broad scraping; guardrails intact;
- normal UI stays simple (editable clue fields are part of the same two-block
  input; developer controls stay collapsed).

## Human gates

None triggered.

## NEXT

Return to control-room review. Real-user pilot remains paused until the fix is
accepted. Durable finder adoption, Google Books credentials and any
Chinese-catalogue resolver remain gated.

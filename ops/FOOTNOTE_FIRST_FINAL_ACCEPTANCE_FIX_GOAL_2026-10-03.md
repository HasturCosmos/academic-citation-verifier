# GOAL — Footnote-first V0.2 final browser-flow acceptance fixes — 2026-10-03

Status: AUTHORIZED routine defect-fix batch under D018.

Baseline fix commit: `0f5b30e720bbcdfe62b19baa402055db3e911e9b`.
Authoritative product definition: `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md` (D022, D023).
Prior acceptance-fix report: `ops/FOOTNOTE_FIRST_ACCEPTANCE_FIX_REPORT_2026-10-03.md`.

## Why this Goal exists

Control-room re-review confirmed that commit `0f5b30e` closes the original four defects in the backend/state layer, but three browser-level continuity defects remain. The 31/31 self-probes do not exercise these exact user interactions.

This is a second bounded acceptance patch. It is not a new product phase, architecture, provider, or retrieval design.

## P0-F — no-PDF result page must actually accept the owned PDF

Current defect:
- the no-PDF finder page tells the user they may "直接上传你合法获得的 PDF";
- but the continuation form contains no `primary_file` input and is not multipart;
- the existing probe manually constructs a POST to `/extract`, so it proves backend carriage but not that the rendered browser UI can perform the upload.

Required:
- on the no-PDF / no-evidence-eligible state, render an actual PDF file input on the continuation form;
- post it to the existing owned-PDF `/extract` path with `multipart/form-data`;
- carry `secondary_text`, `footnote`, and the confirmed `identity_json` without re-entry;
- do not call source search on this owned-PDF continuation;
- keep the "查找这一版" bundle.

## P0-G — clearing a parsed identity field must really clear it

Current defect:
- the identity page says "留空表示未能识别";
- `_identity_from_request` currently includes only non-empty `id_*` values in `overrides`;
- therefore if parsing produced a wrong value and the user deletes it, `build_identity` reparses the old note and restores the value.

Required:
- distinguish "field absent from request" from "field present but intentionally blank";
- every visible `id_*` field posted by the confirmation form is authoritative, including an empty string;
- an intentionally cleared field must not silently reappear from deterministic parsing;
- downstream search/citation metadata must respect the cleared value;
- provenance should remain honest.

## P0-H — edited identity must survive direct owned-PDF upload from the confirmation screen

Current defect:
- the editable identity fields live in one `/find` form;
- the "我已经有对应的中文版 PDF" upload is a separate form containing the pre-edit serialized identity;
- if the user edits bibliographic fields and then chooses the direct upload path, those edits are not submitted and the old parsed identity is used.

Required:
- make the direct owned-PDF action submit the current edited identity values, or introduce the smallest equivalent local confirmation-state step;
- the user must not be forced to run source acquisition just to persist edits;
- the owned-PDF path must remain offline with respect to source acquisition;
- user-edited values win and reach final citation metadata.

## Required acceptance probes

Extend `tools/footnote_first_probes.py` with browser-path checks that fail on `0f5b30e`:

1. render the no-PDF finder state and assert the page contains a real `primary_file` upload control on a multipart form; submit that rendered-path payload and verify confirmed identity reaches `/run` without a second `sa.search_all` call;
2. start from a parsed note with a populated field, submit the identity confirmation with that field intentionally blank, and verify the resulting identity/search/citation state keeps it blank rather than reparsing it;
3. edit identity fields on the confirmation screen, choose the direct owned-PDF route, and verify the edited values — not the original parse — reach final bibliographic metadata/citation;
4. preserve all 31 existing footnote-first checks and all prior regression suites.

Then rerun:
- `tools/mvp_probes.py`
- `tools/t003_regression_probes.py`
- `tools/t004_regression_probes.py`
- `tools/t006_ocr_probes.py`
- `tools/source_acquisition_probes.py`
- `tools/footnote_first_probes.py`

## Constraints

- no new provider, credential, account, paid service, or model call;
- no new dependency expected;
- no new RAG/evidence stack;
- no unauthorized/pirated acquisition or broad scraping;
- preserve source-acquisition guardrails and the existing evidence/highlight pipeline;
- keep the normal UI simple;
- do not reopen D019/D022/D023 or the superseded identity-resolution v2 Goal.

## Docs / state on completion

Update:
- `ops/FOOTNOTE_FIRST_ACCEPTANCE_FIX_REPORT_2026-10-03.md` with a second-fix addendum, or create a dedicated report;
- `AGENTS.md`;
- `ops/PROJECT_STATE.md`;
- `ops/TASK_QUEUE.md`;
- `ops/RUN_LOG.md`.

Do not mark V0.2 pilot-ready until these browser-path probes and all regressions pass and control-room review accepts the result.

## Stop conditions / Human Gates

Stop only for a genuinely new paid/keyed/credentialed source, unauthorized access route, major architecture change, or product-scope change beyond D022/D023.

Routine bugs and reversible implementation choices should be fixed autonomously.

## Definition of done

PASS only when a user can complete the advertised browser workflow without hidden/manual POST construction: edit or clear bibliographic fields, choose either lawful source acquisition or direct owned-PDF upload, and carry the exact confirmed identity into final evidence/citation output without re-entry or silent restoration of rejected values.

# GOAL — Footnote-first V0.2 control-room acceptance fixes — 2026-10-03

Status: AUTHORIZED routine defect-fix batch under D018.

Baseline implementation: commit `9c9290124c57a557c04f485281106c231b7b6100`.
Authoritative product definition: `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md` (D022, D023).

## Why this Goal exists

Control-room review found that the V0.2 surface is visually aligned with the product definition, but several real user paths do not carry the inputs / confirmed bibliographic identity all the way into the evidence-and-citation run. The existing 16/16 footnote-first probes do not cover these gaps.

This is a bounded acceptance patch, not a new product phase or architecture.

## P0-A — normal identify path must ingest secondary-page uploads

The normal primary action posts to `/identify`.

Current defect: `/identify` OCRs `footnote_file` but does not process `secondary_file`. Therefore an advertised flow such as “secondary screenshot/PDF + footnote text/screenshot → identify source” can lose the secondary passage before retrieval.

Required:
- reuse the existing secondary extraction/OCR helper;
- when `secondary_file` is supplied, extract it before identity confirmation;
- preserve the extracted secondary text through `/identify -> /find -> /use_found or user upload -> /run`;
- no new OCR subsystem.

## P0-B — direct owned-PDF path must ingest footnote screenshots

Current defect: the “我已有 PDF，直接上传” path posts to `/extract`, but `/extract` ignores `footnote_file`. A user who supplies the note as a screenshot therefore loses the main navigation clue exactly on the direct-PDF path.

Required:
- reuse the existing image OCR helper for `footnote_file`;
- preserve the OCRed note in the confirmation/run form;
- `sa.search_all` must remain uncalled on the owned-PDF path.

## P0-C — confirmed bibliographic identity must survive continuation and feed citation metadata honestly

Current defects:
- user edits made on the identity-confirmation screen (`id_*`) are rebuilt for `/find` but are not preserved into `/use_found` or the later owned-PDF continuation;
- the “当前没有找到可直接使用的 PDF” page says the resolved identity is kept, but the continuation only carries secondary text / footnote / hints;
- the canonical run receives the footnote as retrieval hints, but the confirmed identity is not carried into bibliographic metadata, so the result can still show “缺少已确认的元数据，未生成引用串” even after the user has confirmed fields.

Required:
- introduce the smallest local state representation needed to carry the confirmed identity across the whole continuation;
- user-confirmed edits win over deterministic parse output;
- never silently convert an original-language work identity into a Chinese-edition claim;
- only fields that are explicitly present in the note or explicitly confirmed/edited by the user may feed citation metadata;
- mark metadata provenance clearly (e.g. note-extracted vs user-confirmed vs source-record metadata);
- source/PDF metadata and user-confirmed metadata may be composed, but conflicts must remain visible instead of being silently overwritten;
- the owned-PDF path still skips source acquisition; an offline identity-confirmation step is allowed and is not source search.

## P1-D — “need more clue” must actually let the user add a clue

Current defect: the “还需要一点脚注线索” page asks the user to supplement the note, but its retry form contains only hidden values and resubmits the same unchanged note.

Required:
- either provide an editable footnote field / footnote-image upload on that page, or return to a prefilled normal form where the user can actually add the missing clue;
- do not broad-search when clues remain insufficient.

## P1-E — keep targeted lookup publication-oriented

Do not broaden providers.

Where confirmed Chinese-container / translator / publisher / year information exists, make the single targeted lookup string prefer/use those confirmed publication clues rather than discarding them behind a generic original-work query. Keep the current bounded network architecture and access guardrails.

## Required acceptance probes

Extend `tools/footnote_first_probes.py` with real HTTP-path checks that would fail on commit `9c929012`:

1. secondary screenshot/PDF + footnote screenshot -> `/identify` -> extracted secondary text and parsed note both survive;
2. owned primary PDF + footnote screenshot -> `/extract` / `/run`; note survives and `sa.search_all` is never called;
3. edit identity fields -> `/find` returns no PDF -> continue to owned-PDF upload -> edited identity survives without re-entry;
4. edit identity fields -> open PDF chosen -> `/use_found` -> run -> edited identity survives;
5. a Chinese note with confirmed author/title/container/translator/publisher/year + PDF lacking metadata -> final result produces citation metadata/citation strings from only those confirmed fields and records provenance;
6. a foreign-language note with no confirmed Chinese-edition metadata must NOT fabricate a Chinese citation;
7. “need more clue” page permits an actual edit/upload before retry;
8. existing text-layer and RapidOCR evidence paths remain unchanged.

Then rerun all existing suites:
- `tools/mvp_probes.py`
- `tools/t003_regression_probes.py`
- `tools/t004_regression_probes.py`
- `tools/t006_ocr_probes.py`
- `tools/source_acquisition_probes.py`
- `tools/footnote_first_probes.py`

## Constraints

- no new provider, credential, account, paid service, or model call;
- no new RAG/evidence stack;
- no unauthorized/pirated acquisition;
- no broad scraping;
- no dependency unless strictly necessary (expected: none);
- preserve the lawful source-acquisition guardrails;
- preserve the existing PDF evidence/highlight pipeline;
- keep normal UI simple; do not re-expose developer controls.

## Docs / state on completion

Update:
- `ops/FOOTNOTE_FIRST_SIMPLIFICATION_REPORT_2026-10-03.md` with an acceptance-fix addendum or create a dedicated fix report;
- `AGENTS.md`;
- `ops/PROJECT_STATE.md`;
- `ops/TASK_QUEUE.md`;
- `ops/RUN_LOG.md`.

Do not mark V0.2 pilot-ready until the new probes and all regressions pass and control-room review accepts the fix.

## Stop conditions / Human Gates

Stop only for a genuinely new paid/keyed/credentialed source, unauthorized access route, major architecture change, or product-scope change beyond D022/D023.

Routine bugs and reversible implementation choices should be fixed autonomously.

## Definition of done

PASS only when the advertised three-block workflow works as a continuous stateful path, including image inputs and the owned-PDF route, and confirmed bibliographic identity reaches citation output without fabrication.

After that: return to control-room review. Real-user pilot is the NEXT stage only after acceptance.

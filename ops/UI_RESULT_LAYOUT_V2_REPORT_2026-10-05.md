# UI Result Layout V2 Report — 2026-10-05

Status: **IMPLEMENTED + REGRESSION PASS / USER VISUAL ACCEPTANCE PENDING**

Branch: `ui-result-page-v0`
Base implementation: `76f6ecd`

## User-confirmed layout

Desktop-first 2.5-column result workspace:

- top-left + top-middle: one source-PDF card spanning both columns;
- left column: compact bibliographic metadata + concise edition-conflict note;
- middle column: merged result/instruction block + candidate list + collapsed "other retrieval candidates";
- right column: currently selected candidate detail (original page + highlight, corresponding Chinese text, footnote + reference citation).

Column widths are intentionally unequal. Mobile layout is not a current design target.

## Candidate interaction

- Multiple-candidate result defaults to the highest-ranked plausible localized candidate **for viewing only**.
- The default is explicitly not a final system confirmation.
- The selected candidate row has a visible selected state and "当前查看" marker.
- Each candidate row stays intentionally minimal: human-readable status + confirmed printed page when available + "展开查看".
- Clicking a candidate switches the right-side detail panel client-side.
- "其他检索候选" stays collapsed below the main candidate list.

No known Golden answer is hard-coded.

## Source-PDF interaction

The source card is now a real upload/drop control:

- displays a PDF icon + current filename;
- spans the left and middle columns as requested;
- supports click-to-select and drag/drop of a replacement PDF;
- choosing a replacement PDF directly starts a rerun of the current citation-verification task;
- the current secondary passage / note / options and confirmed identity (when available) are carried into the rerun;
- replacement PDF metadata is **not** copied from the previous PDF, avoiding false edition metadata.

The new route is `POST /rerun_source`.

## Evidence honesty

- Printed page remains primary; PDF sequence page remains secondary.
- Unlocalized candidates never receive fabricated page highlights or copyable evidence citations.
- OCR remains disclosed to users as "RapidOCR 扫描识别（可选路径）" because OCR provenance is evidence-relevant, not developer trivia.
- The normal result page no longer exposes retrieval model, embedding model, timings, internal run counters, or the "本次运行与调试信息" block.
- Edition conflicts remain visible, but are condensed into a short left-column note rather than the previous verbose full-width block.

## Real Weber preview

The real Golden result was rendered at 1600×1400.

Observed:
- source card spans columns 1–2;
- bibliographic + conflict information sits below it in column 1;
- merged multi-candidate guidance and candidate rows occupy column 2;
- right column shows the currently selected candidate with page images, text and citations;
- selected row is visibly highlighted;
- printed pp.105–106 remains available in the candidate list but is not forced as the default winner;
- developer/debug panel is absent.

## Verification

Final checks after the V2 change:

- MVP/UI probes: **87/87**
  - adds direct source-swap rerun coverage;
  - verifies user-facing debug information is absent;
  - verifies source dropzone, selection semantics, printed-page provenance and edition-conflict visibility.
- T003 localization: **15/15**
- T004 evidence object: **16/16**
- T006 OCR: **5/5**
- source acquisition: **106/106**
- Footnote-first: **58/58**

No new frontend framework or dependency.
No retrieval/ranking/model/provider/OCR architecture change.
No private source material or screenshots added to Git.

## UNIQUE NEXT

User visually reviews the live real-Weber V2 page.

Do not merge to `main` until the user accepts or requests another bounded UI iteration.

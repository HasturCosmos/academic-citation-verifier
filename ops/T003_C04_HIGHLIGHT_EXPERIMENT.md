# T003 — C04 candidate-to-highlight experiment

Status: READY

## Goal

Validate the evidence-delivery slice required by PRODUCT_V0_1 without rerunning T001 retrieval:

saved C04 candidate passage -> exact PDF page -> exact character geometry -> original-page render -> highlighted evidence image + machine-readable evidence record.

This is an experiment, not a final architecture commitment.

## Source of truth

Read first:
1. AGENTS.md
2. ops/PRODUCT_V0_1.md
3. ops/T002_ARCHITECTURE_PLAN.md
4. ops/PROJECT_STATE.md
5. ops/TASK_QUEUE.md
6. newest relevant ops/RUN_LOG.md entries

## Reuse

Reuse the saved T001 C04 candidates and existing private C04 PDF/results.
Do not rerun PaperQA2 retrieval unless a missing artifact makes the experiment impossible.

## Primary route

- Keep existing PaperQA2/pypdf retrieval artifacts unchanged.
- Add only the minimum geometry/evidence layer:
  - pypdfium2 for page text/character geometry and rendering;
  - Pillow for highlight overlay/output.
- Do not introduce Docling/MinerU/OCR unless the primary route fails and the failure is recorded first.

## Implementation requirements

1. Install only the minimal new dependencies required by the primary route.
2. Implement a thin evidence-localization adapter. Keep it separable from retrieval.
3. For each saved candidate:
   - use the stored page range as a localization hint;
   - match the original candidate text against PDFium page text with whitespace-normalized matching while preserving a mapping back to original character positions;
   - never delete arbitrary digits/CJK characters merely to force a match;
   - return located / ambiguous / unmatched / needs_ocr.
4. Cross-page candidates must produce one evidence fragment per page.
5. Render the original page at a practical fixed DPI (plan suggests 144 DPI unless evidence justifies a different value).
6. Produce:
   - original page image;
   - highlighted page image;
   - JSON evidence record containing candidate id, PDF page number, matched text span, character boxes / highlight boxes, coordinate metadata, status, and file references.
7. Keep private source text/images/results under ignored private paths. Public repo/logs should contain only aggregate metrics and non-sensitive diagnostics.
8. No model/API calls are needed for this experiment.

## Acceptance criteria

Primary pass:
- all 10 saved T001 candidates are processed;
- every candidate ends in an explicit status;
- the historical gold candidate localizes to PDF page 109;
- the known cross-page candidate yields correct evidence on both PDF pages 130 and 131;
- located candidates have non-empty, sane highlight geometry and readable original-page screenshots;
- no guessed highlight is emitted for ambiguous/unmatched cases;
- original PDF and historical T001 artifacts remain unchanged;
- model/API calls: 0; model/API cost: 0.

Visual acceptance:
- inspect every produced highlighted screenshot;
- record whether the highlighted region covers the intended candidate text without hiding unrelated text;
- record any failure class precisely.

Regression probes:
- whitespace / line-wrap differences;
- repeated text -> ambiguous;
- missing text -> unmatched;
- cross-page;
- rotated/cropped page if cheaply reproducible from existing material or a synthetic non-private fixture;
- no text layer -> needs_ocr (do not implement OCR in T003).

## If primary route fails

Stop after recording the failure. Do not automatically install or run Docling/MinerU/OCR.

Propose the smallest targeted fallback experiment using Docling provenance only for the failing page(s).

## Repository updates on completion

Update:
- ops/PROJECT_STATE.md
- ops/TASK_QUEUE.md
- ops/RUN_LOG.md

Add a concise public experiment report under ops/ with:
- dependency versions;
- implementation shape;
- aggregate results;
- pass/fail against criteria;
- screenshots reviewed count;
- failure classes;
- zero API-cost confirmation;
- recommendation for T004.

Do not add private PDF text, private images, or raw private result payloads to Git.

## Scope limits

Do not:
- build the UI;
- change source-acquisition architecture;
- change citation-format features;
- optimize PaperQA2 ranking;
- add long-form AI judgment;
- add multi-agent orchestration;
- make a final durable architecture decision.

## Completion condition

The experiment is complete when the evidence layer has been executed and checked against the criteria above, the repository state is synchronized, and a commit is pushed.

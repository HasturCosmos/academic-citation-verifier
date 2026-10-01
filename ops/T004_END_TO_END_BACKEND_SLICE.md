# T004 — End-to-end backend vertical slice

Status: READY

## Goal

Connect the already-proven retrieval and evidence layers into the first real backend product loop:

secondary-source passage -> candidate primary-source passages -> evidence localization -> user-facing evidence objects.

This task is still backend-first. Do not build the full visual UI yet.

## Source of truth

Read first:
1. AGENTS.md
2. ops/PRODUCT_V0_1.md
3. ops/T002_ARCHITECTURE_PLAN.md
4. ops/T003_C04_EVIDENCE_REPORT.md
5. ops/PROJECT_STATE.md
6. ops/TASK_QUEUE.md
7. newest relevant ops/RUN_LOG.md entries

## Reuse-first rule

Reuse:
- T001/PaperQA2 core retrieval path and current local embedding configuration;
- T003 evidence-localization/highlight layer;
- existing private C04 artifacts and metadata already known to the project.

Do not rebuild retrieval, PDF parsing, rendering, OCR, or citation formatting from scratch.

## Scope

Implement one callable backend workflow that takes:
- one secondary-source quotation/paraphrase text;
- one candidate/local primary PDF document reference;
- optional fallible hints/known metadata;

and returns a structured product result containing:
- candidate passages;
- retrieval rank;
- exact PDF page number(s);
- copyable original Chinese text;
- original-page highlight image reference(s);
- localization status: located / ambiguous / unmatched / needs_ocr;
- basic bibliographic metadata only when actually known;
- a basic Chinese citation shell/string assembled only from confirmed metadata.

The workflow must preserve multiple candidates instead of forcing a single winner.

## Important product rules

- Footnotes/hints are fallible; they must not override contradictory primary evidence.
- Unknown bibliographic fields stay empty/unknown. Never invent translator, publisher, year, printed page, etc.
- Do not use PaperQA2's inferred docname (e.g. Rejoice2026) as authoritative metadata.
- Do not generate long interpretive verification essays.
- No automatic claim that a secondary author is "wrong" merely because a match fails.
- Keep PDF sequence page distinct from printed/book page unless the printed page is actually known.
- Multiple candidates should remain visible to the downstream product layer.

## Minimal user-facing evidence object

For each candidate, return a machine-readable object with at least:
- candidate_id
- status
- source_document_id
- retrieval_rank
- original_text
- pdf_page_numbers
- highlighted_image_refs
- original_page_image_refs
- bibliographic_metadata
- basic_footnote_citation
- basic_reference_citation
- warnings / unresolved_fields

The exact schema may be refined during implementation if needed, but keep it simple and documented.

## Citation rule

For this experiment, support one basic Chinese book citation shape only, e.g.:

[德]马克思·韦伯.经济与社会（第一卷）[M].阎克文译.上海:上海人民出版社,2019:118-119.

But:
- use only known metadata;
- if printed page is unknown, do not silently substitute PDF page as book page;
- missing fields must remain visibly unresolved rather than guessed.

## Experiment case

Use historical C04 as the first vertical-slice test.

Input should start from the real secondary-source query/paraphrase used in T001, not from the already retrieved candidate text.

Run retrieval through the existing PaperQA2 core path, then feed returned candidates into the T003 evidence layer.

Do not rely on the old saved candidate list as the only input path for the acceptance run; the point of T004 is to prove the chain is connected.

## Acceptance criteria

The run passes if:
1. one command/function starts from the real secondary-source query and executes the connected backend loop;
2. retrieval returns candidates without using PaperQA2 CLI agent;
3. at least one returned candidate is localized to exact page geometry and produces a highlight image;
4. the historical gold passage appears among the surfaced candidates and its evidence resolves to PDF page 109;
5. multiple candidates remain represented in output;
6. each candidate has an explicit localization status;
7. the result includes copyable original text;
8. citation strings are produced only from confirmed metadata and contain no invented fields;
9. PDF page numbers are not misrepresented as printed book pages;
10. no private source text/images are committed to Git;
11. actual runtime, model/API calls, tokens, and cost are recorded;
12. existing T001/T003 regression checks still pass or are unaffected.

## Cost discipline

Prefer the cheapest already-proven retrieval route.
Do not add new paid model calls beyond what is required to reproduce the T001-style retrieval flow.
Do not add long answer-generation stages if raw candidate retrieval is sufficient.

## Failure handling

If the connected loop fails:
- fix ordinary local implementation/integration issues autonomously;
- if failure requires changing retrieval architecture, introducing Docling/MinerU/OCR, or materially changing PRODUCT_V0_1, stop and record the blocker instead of expanding scope.

## Non-goals

Do not:
- build the final web UI;
- implement image/photo OCR input yet;
- integrate external/full-web source acquisition;
- implement multiple citation styles;
- implement semantic trimming/page-furniture removal unless required to make the vertical slice usable;
- optimize ranking for benchmark prestige;
- add multi-agent orchestration.

## Completion

On completion:
- add a concise report under ops/;
- update PROJECT_STATE, TASK_QUEUE, RUN_LOG;
- run relevant tests/regressions;
- commit and push;
- report commit SHA and PASS/FAIL.

This task does not by itself finalize the durable architecture.

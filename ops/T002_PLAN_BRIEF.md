# T002_PLAN_BRIEF

Status: READY

## Goal

Design the smallest technical route that can satisfy PRODUCT_V0_1's evidence-delivery loop on the existing C04 case:

secondary-source passage -> candidate Chinese primary-source passage -> exact PDF page -> highlightable text coordinates -> original-page screenshot with highlight.

This task is architecture/planning only. Do not start broad implementation before the plan is accepted.

## Product source of truth

Read first:
1. ops/PRODUCT_V0_1.md
2. ops/PROJECT_STATE.md
3. ops/TASK_QUEUE.md
4. ops/DECISIONS.md
5. newest relevant ops/RUN_LOG.md entries
6. AGENTS.md

## Existing evidence to reuse

T001 already proved:
- PaperQA2 can retrieve the correct C04 passage into Top-5 using a thin adapter;
- raw source text and exact PDF page label can be preserved;
- the CLI-agent search path is unsuitable for Chinese;
- PaperQA2 citation metadata inference is unreliable for this Chinese book;
- bge-small-zh-v1.5 + 400-char chunks is practical locally;
- bge-m3 is CPU-impractical in the current local environment.

Do not repeat T001 unless a new test is necessary to answer T002.

## Reuse-first candidates to compare

At minimum consider:
- PaperQA2 core API as retrieval layer;
- Docling as geometry/provenance-preserving PDF parser;
- MinerU as an alternative parser/OCR/layout route;
- PaddleOCR / OCRmyPDF only where OCR is actually needed.

Do not build a custom PDF parser, OCR engine, or RAG stack unless the maintained components materially fail the acceptance target.

## Key architecture question

Can we keep PaperQA2 for candidate retrieval while adding a geometry-preserving parser/evidence layer that returns exact page coordinates for screenshot highlighting?

Compare this with the smallest viable alternative composition if PaperQA2 makes the evidence path unnecessarily awkward.

## Acceptance criteria for the plan

The plan must:
- identify the minimum component stack for V0.1;
- state which parts of PaperQA2 are retained, wrapped, or dropped;
- preserve exact page provenance and highlightable coordinates;
- support text-native PDFs first, with a clear OCR fallback for scanned pages;
- avoid long-form AI analysis by default;
- keep source adapters separate from retrieval/evidence so future databases can be added later;
- define one next executable experiment on C04;
- define pass/fail criteria for that experiment;
- minimize new dependencies and API/token cost;
- call out any irreversible/high-risk architecture decision requiring user approval.

## Non-goals

Do not yet:
- build the full UI;
- integrate Z-Library or other legally ambiguous acquisition sources;
- implement multiple citation styles;
- optimize for Top-1 ranking beyond what is needed for candidate retrieval;
- build multi-agent orchestration;
- redesign the whole repository;
- expand into literature review or paper writing.

## Expected output

Produce a concise architecture plan in the repository, preferably under ops/, with:
- proposed data flow;
- component responsibilities;
- interfaces between parser / retrieval / evidence / source-adapter layers;
- one recommended route and one fallback route;
- the exact next experiment;
- estimated implementation effort and main risks.

Then update TASK_QUEUE / PROJECT_STATE / RUN_LOG consistently.

Do not begin implementation unless the plan itself requires a tiny read-only or zero-cost validation and it is necessary to choose between routes.

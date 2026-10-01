# T006 — Bounded OCR reuse benchmark

Status: PROPOSED — HUMAN GATE REQUIRED BEFORE INSTALLATION OR RUNTIME BENCHMARK.

## Trigger

T005B-01 is a genuinely new real humanities case whose candidate primary source is a 459-page image-only Chinese scan. The current stack correctly returned `needs_ocr`.

This task exists to decide whether the MVP should add a reusable OCR ingestion component, and if so which mature component is the smallest sufficient fit. It must not become an OCR engineering project.

## Reuse-first shortlist

Evaluate maintained candidates before any custom code:

1. **PaddleOCR / PP-OCRv5**
   - strong Chinese OCR focus;
   - Windows support;
   - CPU-capable path;
   - likely strongest direct OCR baseline for printed Chinese.

2. **MinerU**
   - document parser with OCR and structured output;
   - Windows/Linux/macOS support;
   - can automatically detect scanned PDFs and invoke OCR;
   - heavier than a direct OCR engine but may replace more parsing glue.

3. **Docling**
   - document conversion pipeline with pluggable OCR engines;
   - supports OCR through RapidOCR, EasyOCR, Tesseract and other backends;
   - useful because citefact already demonstrates Docling-based academic-PDF workflows.

4. **OCRmyPDF**
   - mature PDF OCR pipeline that adds a searchable text layer while preserving the PDF;
   - Windows supported but brings external Tesseract/Ghostscript setup and Chinese language-pack management;
   - attractive if the goal is to keep the existing PaperQA2 + T003 path unchanged after OCR.

## Phase 1 — static feasibility only

Before installing anything, compare:
- Windows-native installation burden;
- license;
- Chinese simplified/traditional printed-text support;
- CPU viability on the user's machine;
- whether output preserves one-to-one PDF page provenance;
- whether output can feed the existing PaperQA2 + T003 path without redesign;
- whether coordinates/text order are usable for page-accurate evidence;
- dependency/model size and download burden;
- whether an existing project component can be deleted rather than duplicated.

Output a shortlist of at most two candidates for runtime testing.

## Human gate

Do not install models, system packages, OCR engines, Ghostscript/Tesseract, CUDA components, WSL, Docker, or other new runtime dependencies until the user explicitly approves after Phase 1.

If a candidate requires administrator access, a large model download, a system-wide dependency, or a paid/API service, stop and surface that requirement.

## Phase 2 — bounded runtime benchmark (only after approval)

Use the existing private T005B-01 scan. Do **not** OCR all 459 pages initially.

Benchmark a small, fixed representative sample sufficient to evaluate:
- Chinese character accuracy;
- reading order;
- page provenance;
- ability to create/search a text layer or structured text;
- compatibility with existing retrieval/evidence stages;
- runtime and resource use.

Prefer pages already rendered/identified in T005B plus a few body-text pages. Do not use the secondary paraphrase as ground truth primary text.

If two candidates are close, prefer the one that:
1. requires less infrastructure;
2. preserves the current PaperQA2 + T003 evidence path;
3. produces page-stable text;
4. minimizes custom integration code.

## Acceptance output

Create `ops/T006_OCR_REUSE_REPORT.md` with:
- static comparison;
- approved runtime candidates;
- benchmark sample;
- measured results;
- integration/dependency burden;
- ADOPT / PARTIAL_REUSE / KEEP_NO_OCR_FOR_MVP recommendation;
- exact next action if adoption is recommended.

## Guardrails

- no custom OCR model;
- no OCR training/fine-tuning;
- no full 459-page OCR before a sample benchmark passes;
- no architecture rewrite;
- no source acquisition/UI work;
- no assumption that OCR text is source-truth without page-image verification;
- preserve the original scan unchanged under private data.

## Boundary

T006 is a component-selection benchmark. It does not itself authorize a durable OCR dependency or architecture change. Final adoption remains a user decision.

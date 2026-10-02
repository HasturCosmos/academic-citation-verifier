# MVP PRODUCTIZATION GOAL — 2026-10-02

Status: AUTHORIZED FOR LONG-RUN EXECUTION.

## Mission

Turn the accepted backend/evidence experiments into the **first runnable MVP candidate** for **二流文科生的二手文献引用助手**.

The authoritative product definition is `ops/PRODUCT_V0_1.md`. Do not redefine the product around what is easiest to implement.

The user has confirmed D017:
- text-layer PDF path remains default;
- RapidOCR is adopted as the optional scan-ingestion fallback for the MVP;
- OCRmyPDF remains backlog;
- OCR text must always be labeled as OCR and verified against page images.

## Operating mode

This is a long Codex Goal. Continue across adjacent low-risk, reversible tasks without waiting for user confirmation after each checkpoint.

Before work:
1. fast-forward `origin/main`;
2. inspect the actual provider/model/reasoning mode;
3. read `AGENTS.md`, `ops/PROJECT_STATE.md`, `ops/TASK_QUEUE.md`, `ops/DECISIONS.md`, `ops/PRODUCT_V0_1.md`, `ops/OVERNIGHT_REPORT_2026-10-02.md`.

Recommended execution target:
- model: DeepSeek V4.1 Flash
- reasoning: Low
- mode: Goal

Reason: product/architecture decisions and acceptance boundaries are already explicit; most remaining work is implementation, test, packaging and documentation.

## Stage 0 — Reuse scan for the product surface

Before creating a UI/framework, run a bounded Reuse First check:
1. current repo/demo capability;
2. current environment packages;
3. native/installed skills/tools;
4. mature lightweight local UI options.

Preference:
- reuse the existing real HTML/evidence output when sufficient;
- if an interactive local surface is needed, choose the smallest mature framework that materially reduces code;
- do not start a frontend build system, React stack, auth system, cloud deployment, or design system.

Record the choice and why it is smaller than alternatives.

## Stage 1 — reproducible environment

The current machine works but the repo has no committed dependency manifest.

Create the smallest reliable reproducibility path:
- pin/document the Python version;
- record the Python dependencies actually needed for the MVP, including RapidOCR/onnxruntime and existing PaperQA2/evidence dependencies;
- prefer a conventional dependency manifest plus lock/export if practical;
- do not commit local virtualenv/cache/model binaries;
- verify a clean-environment install as far as possible without destructive machine changes.

Do not silently upgrade core dependencies merely to get a newer tool.

Acceptance:
- a fresh developer can follow one documented setup path;
- required dependencies/versions are explicit;
- optional OCR dependencies are clearly separated/labeled if useful.

## Stage 2 — real product entry point

Build one canonical product entry point rather than exposing T00x experiment scripts.

The entry point must route:
- text-native source PDF -> existing text-layer path;
- image-only/scanned source PDF -> RapidOCR optional fallback;
- no usable source/full text -> honest insufficient-source failure.

Minimum user-facing inputs for the MVP candidate:
- secondary-source content: pasted text, uploaded secondary PDF, or uploaded image/photo;
- optional free-form hints;
- one or more currently available primary-source documents/resources (the first MVP may use user-supplied/local source adapters; universal acquisition is not required).

For uploaded secondary PDF/image:
- extract readable text using existing/reused capabilities;
- if multiple plausible quotation/paraphrase items are detected, expose a simple selection step if it can be implemented reliably with the current components;
- if robust automatic multi-item detection would require a new subsystem/paid model, do not invent it: implement the simplest honest selection/manual-crop/text-confirmation fallback and record the remaining product gap.

Hints remain fallible and must never override contradictory primary evidence.

## Stage 3 — result experience

Produce a compact user-facing result view consistent with PRODUCT_V0_1.

For each edition/source:
- candidate count;
- expandable candidate results;
- copyable Chinese original/OCR text;
- original-page image with highlight;
- PDF sequence page;
- printed page only if actually known;
- known bibliographic metadata;
- copyable basic footnote citation;
- copyable reference-list citation;
- warnings/unresolved fields.

Failure states must remain explicit:
1. reliable evidence found;
2. multiple plausible candidates;
3. current source text is searchable but no reliable corresponding passage was found;
4. current sources cannot provide sufficient searchable primary text / source coverage.

Never collapse these into a generic "not found".

For OCR results:
- visibly label OCR origin;
- keep the page-image verification warning;
- do not publish a character-accuracy percentage.

## Stage 4 — two real end-to-end routes

The MVP candidate must demonstrate at least:
- **Route A — text-layer success:** reuse the accepted C04 path without altering the historical source/evidence truth;
- **Route B — scan success:** reuse T005B-01 with the adopted RapidOCR path.

The same canonical product entry point/output contract should drive both routes as much as practical. Do not keep them as two unrelated demo scripts.

Also verify one honest failure mode through the product entry point (for example missing/unavailable source, no searchable evidence, or deliberately missing OCR cache/source coverage) without synthetic success claims.

Private source files and generated evidence stay git-ignored.

## Stage 5 — product cleanup required for demonstration

Fix only defects that materially harm the MVP:
- broken paths;
- repeated page furniture intruding into displayed candidate text/highlights when a bounded deterministic cleanup is safe;
- confusing experimental/T00x language in the user-facing surface;
- missing setup/start instructions;
- crashes on known input types.

Do not spend time on:
- branding;
- animations;
- polished visual design;
- accounts/auth;
- deployment/cloud hosting;
- universal literature acquisition;
- automatic paper writing;
- long interpretive misquotation essays.

Final visual/brand direction remains a Human Gate.

## Stage 6 — tests and acceptance package

Run:
- T003 regression suite;
- T004 regression suite;
- T006 regression suite;
- new product-entry-point tests;
- both real routes from Stage 4;
- dependency/setup smoke checks.

Preserve prior source hashes/integrity.

Create:
- `ops/MVP_CANDIDATE_REPORT_2026-10-02.md`
- concise root `README.md` suitable for a portfolio/open-source reader
- one canonical launch command
- if needed, a demo-data preparation command that references only private local paths and never commits copyrighted/private source bytes.

The report must explicitly score each confirmed PRODUCT_V0_1 requirement as:
- MET
- PARTIAL
- NOT MET / deferred with reason

Do not self-declare MVP success merely because tests pass.

## MVP candidate acceptance bar

The result may be called **MVP candidate** only if:
- a fresh local user can set up and launch it using committed instructions;
- the canonical interface accepts a real secondary input and a real primary source resource;
- text-native and scan routes both work through the same product surface/contract;
- at least one real result shows copyable primary text + page image/highlight + provenance + citation;
- honest failure states remain distinguishable;
- no private/copyright source content is committed;
- regressions stay green.

The result may be called **MVP COMPLETE** only after ChatGPT control-room review and user milestone acceptance. Codex must not make that final acceptance decision.

## Autonomy / stop rules

Autonomously handle:
- ordinary bugs;
- local dependency conflicts;
- reversible refactors;
- test failures;
- UI implementation details;
- report/docs updates.

Stop and record a Human Gate only for:
- money/API keys/new paid services;
- admin/elevation or broad system changes;
- privacy/external upload of source material;
- core product-scope change;
- durable architecture change beyond D017;
- final brand/visual direction;
- destructive/irreversible operation.

If one optional feature blocks, degrade honestly and continue the rest of the MVP candidate instead of stalling the entire run.

## End state

At the end:
1. commit each meaningful checkpoint;
2. push reviewable work to `origin/main`;
3. leave working tree clean;
4. update `ops/PROJECT_STATE.md`, `ops/TASK_QUEUE.md`, `ops/RUN_LOG.md`, `AGENTS.md`;
5. report exact launch command and exact final commit;
6. write one recommended NEXT only.

Do not require the user to relay intermediate logs back to ChatGPT.

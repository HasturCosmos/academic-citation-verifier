# AGENTS.md

## Project mission

Build a real, testable product named **二流文科生的二手文献引用助手**.

The confirmed product definition is `ops/PRODUCT_V0_1.md`.

V0.1 starts from a secondary-source quotation/paraphrase or page (text, PDF, or image), treats footnotes and user hints as fallible clues, searches currently accessible source adapters/resources for corresponding Chinese primary-source full text, and returns traceable primary evidence: copyable original text, page provenance, original-page screenshot/highlight, and basic citation output.

Weber is an evaluation set, not a product whitelist.

## Current priority

Gate 0 product definition is closed. Current engineering priority remains M1 evidence retrieval, now evaluated against PRODUCT_V0_1 rather than the older candidate-PDF-only product scope.

Do not expand into PMS, automatic literature reviews, automatic paper writing, broad knowledge bases, or unnecessary multi-agent architecture.

## Operating loop

Read these files before substantial work:
1. `ops/PROJECT_STATE.md`
2. `ops/TASK_QUEUE.md`
3. `ops/DECISIONS.md`
4. newest relevant entries in `ops/RUN_LOG.md`

Then:
goal -> smallest task -> implement -> test -> record -> gate.

## Reuse-first automatic gate

Treat reuse checking as a mandatory project gate, not an optional reminder.

Trigger the gate whenever work is about to:
- add a new reusable subsystem, parser, retrieval/reranking layer, OCR path, citation/metadata resolver, evidence-grounding layer, report/export framework, agent/workflow infrastructure, or other non-trivial capability;
- materially replace or expand an existing technical route;
- spend significant implementation effort on functionality likely to exist elsewhere.

Before implementation, check in this order, stopping when a mature sufficient solution is found:
1. current repository capabilities and prior project results;
2. ChatGPT / Work / Codex native capabilities;
3. currently available Skills / Plugins / MCPs;
4. installable Skills / Plugins;
5. maintained open-source projects on GitHub;
6. official documentation and established practices;
7. real-world examples from technical communities only when they materially help.

Decision preference:
direct reuse > small adaptation > composition > from-scratch implementation.

For each triggered gate, record a short result:
- what was checked;
- what is reusable;
- what gap remains;
- why custom code is still necessary, if any.

Do not turn this into open-ended research. Skip the gate for trivial, local, reversible implementation details where external reuse would not materially save work.

Current detailed protocol and latest scan: `ops/REUSE_SCAN_2026-10-01.md`.

## Cost rule

Optimize for minimum tokens / API spend while preserving task reliability.

- Use the lowest sufficient reasoning/model setting.
- Do not use Goal / Ultra / multi-agent modes unless parallelism or long-horizon autonomy materially improves the result.
- Before expensive actions, record why cheaper alternatives are insufficient.
- Reuse prior results; do not repeatedly reread large contexts.

## Model rule

Never assume the active Codex model/provider from historical notes.
Before important Codex work, inspect the actual runtime config/provider/model/reasoning mode.
The user currently has a custom DeepSeek-backed Codex configuration available, but live configuration is authoritative.

## Evidence rule

Never fabricate quotations, page numbers, source claims, or retrieval results.

Distinguish:
- source evidence
- retrieval result
- AI analysis
- user/human confirmation
- unresolved items

For citation verification, generated summaries do not count as the source passage.

## Context / drift rule

At each meaningful reply or work unit, internally assess context health:
- GREEN: continue
- YELLOW: finish current unit, then hand off
- RED: stop expansion and create a minimal handoff

Do not resurrect obsolete plans or old learning curricula.

## Repository state contract

GitHub is the shared state bus for Chat / Work / Codex.

After substantive work:
- update `ops/PROJECT_STATE.md` if project state changed;
- update `ops/TASK_QUEUE.md` if task status changed;
- append a concise record to `ops/RUN_LOG.md`;
- update `ops/DECISIONS.md` only for confirmed durable decisions.

Do not silently change durable decisions.

## Current technical direction

T001-T004 are complete and accepted. Do not repeat the PaperQA2 baseline, T003 evidence experiment, or T004 C04 vertical slice.

Current gate:
1. T005A is complete and reviewed: **KEEP_CURRENT**.
2. T005B is complete and reviewed: the first genuinely new real case failed honestly with document-level `needs_ocr`; no OCR was added.
3. T006 Phase 1 is complete: the static comparison and the two shortlisted runtime candidates (OCRmyPDF, RapidOCR) are in `ops/T006_OCR_REUSE_REPORT.md`. Brief: `ops/T006_OCR_REUSE_BENCHMARK.md`.
4. T006 Phase 2 is complete (2026-10-02): the authorized overnight batch `ops/OVERNIGHT_GOAL_2026-10-01.md` ran. OCRmyPDF is recorded `BLOCKED_INSTALL`; RapidOCR benchmarked (459/459 pages OCR'd, no model calls, $0.00) and an **experimental** OCR evidence path validated on the real scan. Recommendation recorded as **PARTIAL_REUSE**; see `ops/T006_OCR_REUSE_REPORT.md`, `ops/T006_DEMO.md`, `ops/OVERNIGHT_REPORT_2026-10-02.md`.
5. The sole NEXT is a Human Gate, not more engineering: decide durable OCR adoption, approve or decline a project-local package-manager route for the blocked OCRmyPDF candidate, settle the printed-page → PDF-page mapping policy, and commission the independent verification (certified human transcription + a second real scan case) owed before any accuracy claim.

Paid/API OCR, administrator/elevation prompts, WSL/Docker/CUDA installation, broad system changes, durable OCR adoption, and final visual/brand decisions remain gated. Do not build custom OCR, and do not present OCR text as source truth without page-image verification.

## Long-Goal default routing

Treat long-run batching as an automatic project behavior, alongside context-health checks and the Reuse-first gate.

Before sending work to Codex:
1. identify the largest coherent unit whose goal and acceptance bar are already clear;
2. bundle adjacent low-risk, reversible, testable work into one Goal;
3. write explicit stop conditions / Human Gates;
4. prefer one start → continuous execution → one final GitHub review over repeated user-mediated checkpoints.

During the Goal:
- continue implementation → test → fix → regression → docs/state updates autonomously;
- do not stop for routine bugs, reversible refactors, dependency conflicts, or ordinary test failures;
- checkpoint meaningful work to GitHub;
- stop only for a genuine Human Gate, a repeated evidence-integrity blocker, or the final reviewable deliverable.

After the Goal:
- ChatGPT should review GitHub directly;
- do not ask the user to copy/paste logs or reports that are already in the repo;
- the user's normal bridge role is only to start Codex once when no direct control connector exists, and to decide actual Human Gates.

If a direct ChatGPT↔Codex control/communication connector becomes available later, use it and remove the manual bridge rather than preserving unnecessary user relay.

## Batch autonomy rule

When adjacent tasks are clear, low-risk, reversible and testable, batch them into one longer Goal instead of requiring user relay after every checkpoint.

- Commit/push each major checkpoint so GitHub remains inspectable.
- Fix ordinary bugs, dependency conflicts, failed tests and reversible implementation details autonomously.
- Stop only at a Human Gate or a repeated evidence-integrity blocker.
- Experimental adapters/UI may be built reversibly without being treated as permanent architecture or final design.
- Never claim ChatGPT itself is running Codex in the background when no control connector exists.

Current authorized batch: `ops/MVP_PRODUCTIZATION_GOAL_2026-10-02.md`. The prior overnight batch is closed. Continue autonomously through reversible productization work until a Human Gate or the final candidate package is reached.

## Current stage — MVP COMPLETE / post-MVP pilot (2026-10-02)

The user explicitly accepted the MVP milestone after ChatGPT control-room review (D019). The accepted baseline is the build documented in `ops/MVP_CANDIDATE_REPORT_2026-10-02.md`.

Do not call this a candidate anymore; the milestone is **MVP COMPLETE**.

Do not reopen these user-deferred items as MVP blockers:
- paid LLM reranking;
- certified human OCR-accuracy verification;
- printed-page mapping;
- same-query multi-edition/multi-translation comparison.

The sole current NEXT is **post-MVP pilot + portfolio/demo packaging**:
- use the accepted MVP on real user literature-tracing tasks;
- record value and failure evidence;
- fix only defects that materially block real use;
- then package a concise internship/demo story.

Do not expand into deployment, accounts, universal acquisition or major architecture without pilot evidence and the normal Human Gate.

D018 remains the default routing rule: batch coherent reversible work into long Codex Goals; GitHub is the state bus; the user is not the message relay.

## Current post-MVP pilot state

The first real user run exposed a P0 primary-source intake bug and an intake UX gap. The authorized patch `ops/POST_MVP_PRIMARY_SOURCE_PATCH_GOAL_2026-10-02.md` is **COMPLETE** (2026-10-02); report `ops/POST_MVP_PRIMARY_SOURCE_PATCH_REPORT_2026-10-02.md`. Blank metadata no longer crashes, uploading a primary-source PDF is the normal web path, EPUB is rejected with an explanation before a job starts, and registered C04/T005B-01 remain labelled demo/cached examples (`mvp_probes` 70/70, T003 15/15, T004 16/16, T006 5/5).

The MVP milestone stays closed and accepted (D019); this was a post-MVP patch, not a new milestone.

Primary-source intake patch has passed control-room review. NEXT: resume real pilot use with a user-supplied primary PDF, record value/failure evidence, and fix only defects that materially block real use before portfolio/demo packaging.

General source acquisition when the user lacks a PDF is a separate subsystem and Human Gate. Do not integrate unauthorized/pirated repositories. Reuse First should evaluate lawful/open/authorized full-text routes when that gate is opened.

## Current post-MVP stage: lawful source-acquisition Phase 1 — COMPLETE (2026-10-02)

The authorized batch `ops/SOURCE_ACQUISITION_OVERNIGHT_GOAL_2026-10-02.md` is
**COMPLETE**. It was executed under D018 long-Goal routing.

- Report: `ops/SOURCE_ACQUISITION_PHASE1_REPORT_2026-10-03.md`; reuse scan:
  `ops/SOURCE_ACQUISITION_REUSE_SCAN_2026-10-03.md`.
- New, reversible, stdlib-only: `tools/source_acquisition.py` (normalized schema +
  six adapters), `tools/source_acquisition_probes.py`, `tools/sa_benchmark.py`,
  plus `③b 查找开放全文` → `/find` → `/use_found` in `tools/mvp_app.py`.
- A real open PDF was lawfully downloaded and verified twice (Internet Archive
  public-domain scan, 524 pages; OpenAlex/ANU Press OA book, 312 pages) and the
  ANU PDF ran through the **unchanged** canonical pipeline (text_layer, 2466
  chunks, 4/5 located, 0 model calls, $0.00).
- For an in-copyright Chinese translation the answer is honestly
  `USER_UPLOAD_REQUIRED`; Internet Archive lending items are refused in code.
- Tests: `mvp_probes` **70/70**, T003 **15/15**, T004 **16/16**, T006 **5/5**,
  new source-acquisition probes **83/83**; 0 model calls, $0.00.
- Google Books is HTTP 429 on the anonymous daily quota; OAPEN/DOAB DSpace REST
  answers this machine with 403 while their OAI-PMH endpoint answers.

Source-acquisition Phase 1 has passed control-room review as an **experimental, reversible** capability. The two control-room hardening items are now **COMPLETE (2026-10-03)**, report `ops/SOURCE_ACQUISITION_GUARDRAIL_PATCH_REPORT_2026-10-03.md`: an Internet Archive item must carry an explicit rights/licence/public-domain signal (only Project Gutenberg is trusted on collection membership alone), and an OpenAlex PDF is evidence-eligible only when the location that carries it is itself marked open access. The hardened finder was re-verified live (all three benchmark cases matched; the ANU OA book downloaded byte-identically and ran through the unchanged pipeline; source-acquisition probes now 98/98), 0 model calls, $0.00.

Guardrail patch has passed control-room review. NEXT: run a guarded real pilot with the hardened experimental finder on the user's own literature-tracing tasks and record value/failure evidence. Do **not** create a Google Books API key or broaden provider integrations yet unless pilot evidence shows the current finder is materially insufficient.
Durable adoption, paid services, credentials, login/borrowing automation and any
architecture expansion beyond the thin optional finder remain gated. The normal
primary-PDF upload path is unchanged and remains the primary route.

## Current authorized batch: source-acquisition guardrail hardening — COMPLETE (2026-10-03)

Brief: `ops/SOURCE_ACQUISITION_GUARDRAIL_PATCH_GOAL_2026-10-03.md` (D018 long-Goal routing, before real pilot use). Executed and verified under the two guardrails above; report `ops/SOURCE_ACQUISITION_GUARDRAIL_PATCH_REPORT_2026-10-03.md`. No new provider, credential, paid service or architecture expansion was added.

## Current authorized batch: footnote-first MVP simplification

Authoritative product spec: `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md`.

Execute `ops/FOOTNOTE_FIRST_SIMPLIFICATION_LONG_GOAL_2026-10-03.md` under D018.

The earlier `ops/IDENTITY_RESOLUTION_V2_LONG_GOAL_2026-10-03.md` is superseded before execution and must not be run.

Normal workflow: secondary quote/paraphrase + corresponding footnote/endnote -> targeted cited-work / Chinese-container resolution -> matching PDF (upload or lawful accessible source) -> unchanged evidence/highlight/citation pipeline.

Do not expose broad source discovery, demo sources, provider diagnostics or technical controls in the normal UX. Do not integrate unauthorized/pirated acquisition.

## Human gates

The user confirms:
- product-scope changes;
- durable architecture choices;
- acceptance of milestone results;
- any action with meaningful external side effects or materially higher cost.

Routine low-risk repo analysis, test execution, and state bookkeeping should be automated where possible.

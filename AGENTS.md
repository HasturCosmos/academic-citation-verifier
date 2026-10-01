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
3. T006 is the proposed sole NEXT: a bounded OCR **Reuse First** benchmark. Brief: `ops/T006_OCR_REUSE_BENCHMARK.md`.

T006 Phase 1 may perform static comparison only. Do not install an OCR engine, model, Tesseract/Ghostscript, WSL/Docker/CUDA component, or other new runtime dependency until the user explicitly passes the human gate. Do not build custom OCR.

## Human gates

The user confirms:
- product-scope changes;
- durable architecture choices;
- acceptance of milestone results;
- any action with meaningful external side effects or materially higher cost.

Routine low-risk repo analysis, test execution, and state bookkeeping should be automated where possible.

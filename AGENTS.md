# AGENTS.md

## Project mission

Build a real, testable AI academic citation verification assistant.

V1 scope:
given (1) a secondary-source quotation/paraphrase and (2) a candidate primary-source PDF,
find the most likely original passage, preserve page/source provenance and context, assist with support judgment, require human confirmation, and keep a reusable verification record.

## Current priority

M1 only: evidence retrieval.

Do not expand into PMS, automatic literature reviews, automatic paper writing, broad knowledge bases, or unnecessary multi-agent architecture.

## Operating loop

Read these files before substantial work:
1. `ops/PROJECT_STATE.md`
2. `ops/TASK_QUEUE.md`
3. `ops/DECISIONS.md`
4. newest relevant entries in `ops/RUN_LOG.md`

Then:
goal -> smallest task -> implement -> test -> record -> gate.

## Research-first rule

Before building a reusable subsystem from scratch, quickly check whether a maintained open-source project/component already solves it.
Preference:
direct reuse > small adaptation > composition > from-scratch implementation.

Do not turn this into open-ended research.

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

Research-first concluded that M1 should not start by hand-building a RAG stack.

Experiment order:
1. PaperQA2-first baseline.
2. Only if the real baseline fails materially, evaluate MinerU 4 + existing hybrid retrieval / related parser alternatives.

Do not test both stacks in parallel without a concrete reason.

## Human gates

The user confirms:
- product-scope changes;
- durable architecture choices;
- acceptance of milestone results;
- any action with meaningful external side effects or materially higher cost.

Routine low-risk repo analysis, test execution, and state bookkeeping should be automated where possible.

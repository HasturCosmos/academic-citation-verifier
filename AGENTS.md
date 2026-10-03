# AGENTS.md

## Project mission

Build a real, testable product named **二流文科生的二手文献引用助手**.

The current product definition is `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md` (D022, D023). Historical `ops/PRODUCT_V0_1.md` remains an archive of the earlier accepted scope.

Current normal workflow: secondary quotation/paraphrase + corresponding footnote/endnote -> targeted cited-work / Chinese-publication resolution -> matching PDF (upload or lawful accessible source) -> traceable Chinese primary evidence: copyable original text, page provenance, original-page screenshot/highlight, and copyable Chinese citation.

Weber is an evaluation set, not a product whitelist.

## Current priority

Gate 0 product definition is closed. The active product is Footnote-first V0.2 (D022/D023). The first bounded acceptance fix is complete at `0f5b30e`; control-room re-review's three browser-flow defects are now closed by the final bounded fix `ops/FOOTNOTE_FIRST_FINAL_ACCEPTANCE_FIX_GOAL_2026-10-03.md` (**COMPLETE**, `ops/FOOTNOTE_FIRST_FINAL_ACCEPTANCE_FIX_REPORT_2026-10-03.md`): the no-PDF page renders a real owned-PDF upload, a cleared identity field stays cleared, and identity-screen edits survive the direct owned-PDF upload. The immediate priority is control-room re-review of that fix; real pilot remains paused until that review passes.

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

The historical MVP milestone D019 remains accepted. Do not reopen T001-T006, the old identity-resolution v2 Goal, or earlier OCR/source-acquisition experiments as active work.

Footnote-first V0.2 implementation exists at commit `9c929012`, but control-room acceptance on 2026-10-03 found state-continuity gaps in the advertised three-block workflow: secondary-page upload is not consumed by `/identify`; footnote-image upload is not consumed by the owned-PDF `/extract` path; confirmed identity does not survive all continuation routes into citation metadata; and the insufficient-clue retry cannot actually accept a new clue.

Active fix brief: `ops/FOOTNOTE_FIRST_ACCEPTANCE_FIX_GOAL_2026-10-03.md`.

Do not start a real pilot or another architecture expansion until this bounded patch is green and accepted.

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

Current authorized batch: `ops/FOOTNOTE_FIRST_ACCEPTANCE_FIX_GOAL_2026-10-03.md`. This is a bounded routine defect-fix batch under D018; no new architecture/provider/credential is authorized. After execution, return to control-room review before real pilot.

## Current stage — MVP COMPLETE / post-MVP pilot (2026-10-02)

The user explicitly accepted the MVP milestone after ChatGPT control-room review (D019). The accepted baseline is the build documented in `ops/MVP_CANDIDATE_REPORT_2026-10-02.md`.

Do not call this a candidate anymore; the milestone is **MVP COMPLETE**.

Do not reopen these user-deferred items as MVP blockers:
- paid LLM reranking;
- certified human OCR-accuracy verification;
- printed-page mapping;
- same-query multi-edition/multi-translation comparison.

The sole current NEXT is **control-room re-review of the completed Footnote-first V0.2 acceptance fixes**. After PASS, resume post-MVP pilot + portfolio/demo packaging on the footnote-first surface:
- use the accepted product on real user literature-tracing tasks;
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

## Footnote-first V0.2 simplification — IMPLEMENTATION COMPLETE + ACCEPTANCE FIX COMPLETE / RE-REVIEW PENDING (2026-10-03)

Authoritative product spec: `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md` (D022, D023).
Brief: `ops/FOOTNOTE_FIRST_SIMPLIFICATION_LONG_GOAL_2026-10-03.md`.
Report: `ops/FOOTNOTE_FIRST_SIMPLIFICATION_REPORT_2026-10-03.md`.
Reuse scan: `ops/FOOTNOTE_FIRST_REUSE_SCAN_2026-10-03.md`.

Executed under D018. The earlier `ops/IDENTITY_RESOLUTION_V2_LONG_GOAL_2026-10-03.md`
was superseded before execution and was **not** run.

Normal workflow is now: secondary quote/paraphrase + corresponding footnote/endnote
-> targeted cited-work / Chinese-container resolution (user-editable confirmation)
-> matching PDF (upload or lawful accessible source) -> unchanged
evidence/highlight/citation pipeline.

New, reversible, stdlib-only: `tools/footnote_parse.py` (deterministic note parser
and cited-work vs containing-publication model) and `tools/footnote_first_probes.py`.
`tools/mvp_app.py` now has three normal blocks (① quote/paraphrase, ② footnote/endnote,
③ primary source with "识别来源并开始核验" + "我已有 PDF"), a `POST /identify`
confirmation step, and a simplified result page (对应中文版原文 / 原页高亮与页码 /
书目信息 / 一键复制引用). Demo sources, `k`, OCR mode, local path, metadata JSON,
provider diagnostics and the free-standing finder are collapsed into 开发者 / 高级选项.

A bounded live Reuse Scan of Crossref / Open Library / Wikidata found **no** no-key
route that resolves a foreign work to its Chinese publication/container; that remains
a documented, gated gap (deterministic parse + user confirmation + upload carry it).
Do not integrate unauthorized/pirated acquisition.

Tests (0 model calls, $0.00): `mvp_probes` **70/70**, T003 **15/15**, T004 **16/16**,
T006 **5/5**, `source_acquisition_probes` **98/98**, `footnote_first_probes` **38/38**.
The single-network-call invariant is preserved (one `sa.search_all(` in `mvp_app.py`,
reached only from `POST /find`; the pipeline never imports the finder).

Control-room acceptance fix is **COMPLETE** (2026-10-03):
`ops/FOOTNOTE_FIRST_ACCEPTANCE_FIX_REPORT_2026-10-03.md`. It closes the four
blocking findings — `/identify` consumes `secondary_file`, owned-PDF `/extract`
consumes `footnote_file`, the confirmed `id_*` identity survives all continuation
routes and feeds citation metadata honestly (provenance recorded, conflicts kept
visible, no foreign-edition-as-Chinese-citation fabrication), and the
insufficient-clue page accepts a real new clue. `footnote_first_probes` grew from
16 to **31** real HTTP-path checks; the single-network-call invariant and the
accepted evidence routes are unchanged.

Final browser-flow fix **COMPLETE** (2026-10-03):
`ops/FOOTNOTE_FIRST_FINAL_ACCEPTANCE_FIX_REPORT_2026-10-03.md`. It closes the
three re-review gaps — the no-PDF finder page renders a real multipart
`primary_file` upload, intentionally-blank `id_*` edits really clear the parsed
value (provenance kept honest), and the identity-screen direct upload submits the
current edits (same form, `formaction='/extract'`) into the final citation
metadata. `footnote_first_probes` grew from 31 to **38**; the single-network-call
invariant and the accepted evidence routes are unchanged.

NEXT: return to control-room re-review of the final fix. Real pilot is paused
until that review passes. Durable finder adoption, Google Books credentials and
any Chinese-catalogue resolver remain gated.

## Human gates

The user confirms:
- product-scope changes;
- durable architecture choices;
- acceptance of milestone results;
- any action with meaningful external side effects or materially higher cost.

Routine low-risk repo analysis, test execution, and state bookkeeping should be automated where possible.

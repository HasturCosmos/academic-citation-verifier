# OVERNIGHT GOAL — 2026-10-01

Status: AUTHORIZED FOR REVERSIBLE EXECUTION.

## Purpose

Reduce human relay. Run the next verified sequence as one long Codex Goal and leave GitHub in a clean, reviewable state by the end.

The user explicitly approved T006 Phase 2 and requested that low-risk, reversible work be batched rather than requiring a ChatGPT/Codex round-trip after every small gate.

This Goal does **not** authorize durable architecture adoption, paid services, irreversible machine changes, product-scope changes, or final visual/brand decisions.

## Runtime routing

Before work, inspect the live Codex provider/model/reasoning mode.

Recommended execution target:
- model: DeepSeek V4.1 Flash
- reasoning: Low
- mode: Goal

Reason: the plan, ordering, stop conditions and acceptance evidence are already explicit; this is primarily execute -> test -> fix -> record work.

If a genuinely architectural decision is required, stop that branch of work and record the decision request rather than silently escalating.

## Stage A — T006 Phase 2 bounded OCR benchmark

1. Sync `origin/main` with fast-forward only.
2. Read:
   - `AGENTS.md`
   - `ops/PROJECT_STATE.md`
   - `ops/TASK_QUEUE.md`
   - `ops/T006_OCR_REUSE_BENCHMARK.md`
   - `ops/T006_OCR_REUSE_REPORT.md`
3. Freeze the small benchmark sample **before** running either engine.
4. Use only the two Phase-1 shortlisted candidates:
   - OCRmyPDF
   - RapidOCR
5. Installation authorization for this benchmark is granted, subject to the safety limits below.
6. Do not OCR all 459 pages until the fixed sample has been evaluated.
7. Measure what can be measured honestly:
   - Windows install/runtime burden;
   - Chinese text output on the fixed sample;
   - reading order;
   - page provenance;
   - geometry/boxes where applicable;
   - whether PaperQA2/T003 can consume the output;
   - runtime/resource burden;
   - regression impact.
8. Ground-truth honesty:
   - use independent hand transcription/visual verification only if the active runtime can actually inspect the page images reliably;
   - never use one OCR engine's output as the other's ground truth;
   - never use the secondary paraphrase as primary-text ground truth;
   - if no independent ground truth can be produced safely, do **not** invent CER/accuracy numbers. Record the limitation and compare only the properties actually observed.
9. Re-run T003/T004 regressions affected by the experiment and re-check C04 integrity.
10. Fill `ops/T006_OCR_REUSE_REPORT.md` measured-results sections.

### Installation safety

Allowed without asking again:
- project-local Python packages inside the existing project environment;
- model/data downloads needed by the two shortlisted OCR candidates, provided they are free and documented;
- reversible local experiment files under ignored private/cache paths.

Do **not** perform without another human gate:
- paid/API OCR;
- administrator/elevation prompts;
- WSL/Docker/CUDA installation;
- destructive PATH/registry edits;
- disabling security controls;
- replacing the user's existing Python/toolchain;
- other broad system-wide changes.

For OCRmyPDF: if Ghostscript/Tesseract cannot be made available without elevation or broad system modification, record `BLOCKED_INSTALL` for that candidate and continue with RapidOCR. Do not let one blocked candidate waste the whole run.

## Stage B — experimental OCR integration, only if evidence supports it

After Stage A, do **not** make a durable ADOPT decision.

You may choose an **experimental winner** only to continue reversible testing if:
- it produces usable Chinese text on the fixed sample;
- page identity remains stable;
- no evidence-integrity rule is broken;
- its integration path is local/reversible;
- regressions remain green.

Then:
1. implement the thinnest experimental adapter necessary;
2. keep it clearly marked experimental/optional;
3. do not delete the existing non-OCR path;
4. preserve the original scan unchanged;
5. if possible, rerun T005B-01 through the experimental OCR path;
6. only after the sample passes may a larger local OCR run be attempted, and only if runtime/disk estimates are reasonable and no new Human Gate is crossed;
7. never claim permanent architecture adoption.

If Stage A is inconclusive, skip Stage B and continue to Stage C using already-proven non-OCR cases.

## Stage C — produce a reviewable demo if the backend state permits

Goal: maximize the chance that the user wakes up to something demonstrable without pretending the MVP is complete.

Trigger this stage if either:
- experimental OCR integration reaches a stable evidence object; or
- OCR remains blocked/inconclusive but the already-proven C04 success path + T005B honest-failure path are intact.

Before adding a demo surface, do a **bounded Reuse First check** of the current environment and mature lightweight local UI options. Do not start a frontend project.

Preferred output order:
1. one-command local demo harness;
2. minimal local web UI only if a mature lightweight dependency is already available or can be added project-locally without admin/system services;
3. otherwise a CLI + generated local HTML/evidence report is acceptable.

The demo must:
- accept or clearly model the product's real inputs;
- show at least the proven `located` path and honest failure status;
- display source text only when actually retrieved;
- preserve PDF/source page provenance;
- display highlight/original-page evidence where available;
- show unresolved fields honestly;
- keep private PDFs/screenshots out of Git;
- have a short README / launch command;
- be explicitly labeled **experimental demo**, not final UI or final brand.

Do not spend time on branding, animations, auth, deployment, cloud hosting or visual polish.

## Stage D — test, checkpoint, and handoff

At each major stage:
- commit meaningful results;
- keep reports/state synchronized;
- do not leave uncommitted product changes;
- do not silently change durable decisions.

At the end:
1. run the relevant zero-cost regressions;
2. record exact dependencies added and where;
3. record model/API calls and cost;
4. update `ops/PROJECT_STATE.md`;
5. update `ops/TASK_QUEUE.md`;
6. append `ops/RUN_LOG.md`;
7. create `ops/OVERNIGHT_REPORT_2026-10-02.md` summarizing:
   - what completed;
   - what failed/blocked;
   - benchmark evidence;
   - experimental demo status and launch command if any;
   - exact commits;
   - remaining Human Gates;
   - one recommended NEXT.
8. push all completed, reviewable work to `origin/main`.

## Stop conditions

Stop expansion and write the overnight report if any of the following occurs:
- money/payment/API key is required;
- admin/elevation or broad system modification is required;
- private data would need to be committed or uploaded externally;
- core product goal/scope must change;
- a permanent OCR architecture choice is required;
- final brand/visual direction is required;
- tests show evidence integrity is compromised and cannot be repaired locally;
- the same blocker repeats after reasonable bounded debugging.

Ordinary dependency conflicts, local test failures, reversible refactors, and implementation details are **not** stop conditions; fix them autonomously.

## Success levels

The overnight Goal may finish at any honest level:

- **Level 1:** T006 Phase 2 benchmark complete and reviewable.
- **Level 2:** Level 1 + experimental OCR adapter validated on sample/real case.
- **Level 3:** Level 2 (or proven non-OCR backend) + one-command experimental demo.

Do not claim Level 3 if only mock data is shown. Do not claim MVP completion unless the confirmed PRODUCT_V0_1 acceptance boundary is actually met.

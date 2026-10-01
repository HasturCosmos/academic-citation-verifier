# T005A — Evidence-layer reuse benchmark

Status: PROPOSED — do not expand beyond this gate.

## Why this task exists

The post-T004 Reuse Scan found a strong overlap between the custom T003 evidence-localization layer and the open-source `docushell/ethos` project.

Before expanding the product, determine whether Ethos should replace or shrink the current custom pypdfium2/Pillow evidence layer.

This task is explicitly about avoiding unnecessary custom engineering. It is not a new product feature.

## Inputs to reuse

Reuse existing artifacts only:
- C04 source PDF already under `data/private/C04/`;
- T004/T003 stored candidates and expected page outcomes;
- existing T003/T004 regression probes;
- current project Python environment.

Do NOT rerun PaperQA2 retrieval.
Do NOT spend model/API tokens.
Do NOT modify private source material.

## Phase 1 — static feasibility audit

Inspect the current Ethos repository/docs and determine:
- exact license and embedding/integration surface;
- whether a Windows-compatible runnable path exists without a new system-wide toolchain;
- whether Python integration still requires an external Ethos CLI;
- whether caller-supplied PDFium is required;
- whether output exposes page coordinates/crops sufficient for our original-page evidence UI;
- whether cross-page evidence and explicit OCR-required behavior are supported;
- what Ethos does NOT do (semantic matching, OCR, claim truth judgment).

If a clean isolated Windows run requires installing a system-wide Rust toolchain or materially expanding the environment, STOP before installation and record that integration burden. Do not install infrastructure merely to complete the benchmark.

## Phase 2 — runtime comparison only if Phase 1 is cheap

If Ethos can be exercised in the existing environment with only reversible project-local dependencies, run it against the existing C04 source/candidate evidence.

Compare against T003:
- Chinese passage localization;
- PDF page accuracy;
- coordinates/crop output;
- cross-page evidence;
- unmatched / repeated-text ambiguity / OCR-required behavior where Ethos exposes equivalents;
- runtime;
- output/provenance schema;
- amount of current T003 custom code that could actually be deleted.

No model/API calls.

## Acceptance output

Create `ops/T005A_ETHOS_REUSE_REPORT.md` with one of three results:

- **ADOPT** — Ethos clearly replaces substantial T003 custom code without losing current behavior or adding material MVP burden.
- **PARTIAL_REUSE** — only a bounded component/schema is worth adopting; specify exactly what.
- **KEEP_CURRENT** — current T003 adapter is thinner/easier for the MVP; record Ethos as a future option.

The report must include:
- evidence for the decision;
- exact custom files/lines/components that would be removed or retained;
- dependency/runtime implications;
- whether any T003/T004 regression expectation would change.

## Guardrails

- no UI work;
- no OCR implementation;
- no source acquisition work;
- no PaperQA2 rerun;
- no architecture rewrite;
- no system-wide dependency installation solely to make Ethos work;
- no deletion of current T003 code during the benchmark.

## Next after T005A

After the reuse decision, return to real-case generalization: run a new real case that naturally exercises an honest failure state (`ambiguous`, `unmatched`, or `needs_ocr` / equivalent), using whichever evidence layer wins this gate.

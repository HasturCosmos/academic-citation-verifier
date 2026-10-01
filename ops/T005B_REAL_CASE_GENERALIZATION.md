# T005B — Real-case generalization gate

Status: READY FOR INPUT — not started.

## Goal

Move beyond the single successful C04 case and test the current connected pipeline on a genuinely new academic case.

The first priority is to obtain real, not synthetic, evidence for at least one honest failure-state path:
- multiple plausible matches / ambiguity;
- no reliable corresponding passage;
- source PDF lacks a usable text layer and therefore needs OCR.

The case must come from real academic material, not a fixture manufactured to trigger a status.

## Required input

Minimum viable case:
1. a real secondary-source quotation, paraphrase, or page that the user actually wants to trace;
2. whatever real source clue is available (footnote, author/title/page memory, etc.; clues may be wrong);
3. a candidate primary-source PDF if one is already available.

Preferred:
- a case not used in T001-T004;
- if the user already has a genuinely troublesome/scanned/mis-hinted case, use that first.

Do not require the user to clean or standardize the clues before ingestion.

## Reuse

Reuse the current stack:
- PaperQA2 core retrieval path where applicable;
- T003 pypdfium2/Pillow evidence localization;
- T004 evidence-object contract;
- existing regression suites.

Do not re-run C04 as the primary evidence for this gate.

## Execution

1. Preserve the raw user input and uncertain clues separately from confirmed metadata.
2. Run the smallest connected path needed for the new case.
3. Record whether the result is:
   - located;
   - ambiguous;
   - unmatched;
   - needs_ocr;
   - or another clearly explained capability/source-coverage limitation.
4. Do not force a match.
5. If the case exposes a concrete missing capability, trigger the Reuse-first gate before writing a new subsystem.
6. If OCR is needed, stop at the explicit OCR requirement; do not build OCR inside T005B.
7. Preserve page provenance and private-source boundaries.
8. Re-run only the regression checks touched by the new case.

## Acceptance evidence

Create `ops/T005B_REAL_CASE_REPORT.md` with:
- case provenance and privacy-safe identifier;
- raw input type and clues used;
- source/candidate material available;
- observed result/status;
- evidence pages or explicit failure evidence;
- whether the status is honest and reproducible;
- runtime/API cost;
- any newly exposed product gap;
- whether the gap can be solved by existing reusable components.

## Pass condition

T005B passes when a genuinely new real case runs through the current product path without invented evidence, and the system either:
- returns traceable source evidence correctly; or
- fails honestly with a reproducible explicit status.

A real failure-state result is especially valuable because T004 covered only `located` on live material.

## Guardrails

- no UI work;
- no architecture rewrite;
- no custom OCR build;
- no universal source acquisition;
- no synthetic case used as the sole acceptance evidence;
- no silent correction of the user's clues;
- no claim that a source/work does not exist when current source coverage is insufficient.

## Human input gate

This task cannot start until one new real academic case is available to the local runtime.
If a suitable case already exists under local private project data, Codex may identify it without exposing private text to Git. Otherwise the user supplies the minimum viable case above.

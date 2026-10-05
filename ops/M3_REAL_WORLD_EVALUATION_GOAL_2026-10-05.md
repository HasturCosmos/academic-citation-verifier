# M3 REAL-WORLD EVALUATION GOAL — 2026-10-05

Status: ACTIVE
Owner: product control / evaluation
Base: main@270acaf

## 1. Why this stage exists

M1 evidence retrieval and M2 end-to-end MVP are functionally running.
The result-page UI has passed user visual acceptance and has been merged to main.

The next milestone from the project migration baseline is M3: test the product on
real academic materials and measure where it works, misses, misleads, or costs too much.

This is an evaluation stage, not a feature-expansion stage.

## 2. Reuse-first decision

Reuse existing product and evaluation assets. Do not build a new benchmark framework.

Existing reusable baselines:
- Pilot Case 001 — Weber Golden Demo (real paraphrase + real PDF + edition conflict);
- C04 / T003 evidence-localization artifacts (long text-layer PDF, cross-page localization);
- T005B-01 / T006 — Plato Republic scan (real scan, RapidOCR path, canonical-location clues);
- existing MVP/UI, T003, T004, T006, source-acquisition and Footnote-first probes.

These are regression/baseline cases, not sufficient by themselves to establish generalization.

## 3. M3 scope

Evaluate the current MVP on a small, bounded real-case set.

### Baseline replay
Replay and summarize the already-known cases above without tuning to them.

### Fresh cases
Add 2–3 genuinely new academic verification cases that:
- were not used to tune ranking, localization, OCR, or UI;
- contain a real secondary quotation/paraphrase plus the corresponding candidate primary PDF;
- preferably include at least:
  - one text-layer PDF;
  - one non-verbatim paraphrase;
  - one case with a meaningful qualifier / scope condition / ambiguity;
  - scan/OCR only if a suitable fresh scan is available without new infrastructure.

Do not broaden into web-wide source acquisition.

## 4. Required measurements

For every case record:

1. input provenance and source edition;
2. whether the true passage is present in Top-1 / Top-3 / Top-5 / Top-10;
3. rank of the human-confirmed best passage;
4. whether the passage localizes to the correct original page(s);
5. printed-page provenance when verifiable;
6. highlight correctness;
7. false-positive / misleading candidates;
8. whether the secondary claim is:
   - directly supported,
   - partially supported,
   - unsupported,
   - ambiguous / requires human judgment;
9. important qualifiers or context omitted by the secondary source;
10. whether the product exposes uncertainty honestly;
11. latency;
12. model/API calls and monetary cost;
13. whether a non-technical humanities user can finish the task from the normal UI.

## 5. Guardrails

- Do not tune ranking or hard-code answers while a case is being evaluated.
- Do not repair a secondary citation silently.
- Do not invent source text, page numbers, metadata, highlights, or certainty.
- OCR text is not source truth; page-image verification remains required.
- Existing accepted product behavior stays frozen during the first evaluation pass.
- If a bug blocks a case, record the failure first. Only then create a separate bounded fix task.
- No new provider, credential, paid service, frontend framework, or architecture change without a separate Human Gate.

## 6. Acceptance criteria

M3 first pass is complete when:

- all existing baseline cases are replayed and summarized;
- at least 2 fresh real cases run end to end;
- every case has a human-confirmed gold judgment recorded separately from system output;
- Top-k retrieval, localization/highlight, claim-support judgment, latency and cost are recorded;
- failures are classified rather than hidden;
- no case is tuned during measurement;
- a single evaluation report answers:
  - what the MVP can reliably do now;
  - where it still fails;
  - whether the MVP is strong enough for portfolio/demo use;
  - the one highest-value product gap to fix next.

## 7. Explicitly out of scope

- broad source-provider expansion;
- automatic literature review;
- knowledge-base construction;
- PMS;
- mobile UI;
- ranking optimization before baseline measurement;
- marketing accuracy claims from this small sample.

## 8. Tool routing

Current step: evaluation design + baseline replay.

Use existing local harnesses and Git-tracked reports first.
No Codex feature implementation is needed to start M3.

If a bounded bug fix becomes necessary later:
- default execution: DeepSeek V4.1 Flash, Goal mode, low/medium reasoning;
- escalate to GPT6 High only for architecture/product-definition or hard debugging;
- do not use GPT6 Ultra unless High demonstrably fails on a high-risk blocker.

## 9. UNIQUE NEXT

Create the M3 baseline evaluation table from existing Weber / C04 / T006 evidence,
then identify the minimum fresh-case input still needed from the user.

Do not change product behavior while producing that baseline.

# POST-MVP GUARDED FINDER PATCH GOAL — 2026-10-03

Status: AUTHORIZED LOW-RISK LONG GOAL.

## Mission

Harden the experimental lawful source finder before real-user pilot use.

Do not expand provider scope. Do not create credentials. Do not redesign the UI.

## Required changes

1. Internet Archive rights guard
   - do not treat broad collection membership alone (`americana`, `opensource`) as sufficient evidence that a PDF is lawful/open for automatic acquisition;
   - prefer explicit item/file rights, license, public-domain or no-known-copyright signals;
   - `gutenberg` may remain a narrow stronger special case if current metadata evidence supports it;
   - lending / print-disabled / private / access-restricted items remain hard rejects.

2. OpenAlex location guard
   - a work-level OA flag alone is not sufficient;
   - the selected PDF location itself must carry a clear OA/access signal before it is evidence-eligible;
   - preserve license metadata when available;
   - if the location has a PDF URL but lacks a clear OA/access signal, downgrade it to discovery-only / not evidence-eligible.

3. Keep download validation unchanged or stricter
   - http(s) only;
   - %PDF header required;
   - size cap;
   - private git-ignored destination;
   - provenance JSON with provider / URL / license / sha256.

4. Add focused regression probes
   - IA americana-only record -> NOT evidence eligible;
   - IA opensource-only record -> NOT evidence eligible unless explicit rights/license signal;
   - IA explicit public-domain/right signal -> eligible;
   - IA lending/restricted still refused;
   - OpenAlex work OA + location pdf_url but location not OA -> not evidence eligible;
   - OpenAlex location is_oa true + pdf_url -> eligible;
   - existing benchmark/open cases still pass if their provider data genuinely carries sufficient signals.

5. Run all relevant zero-cost suites
   - source_acquisition_probes
   - mvp_probes
   - T003
   - T004
   - T006

6. Update:
   - ops/PROJECT_STATE.md
   - ops/TASK_QUEUE.md
   - ops/RUN_LOG.md
   - AGENTS.md
   - create ops/SOURCE_ACQUISITION_GUARDRAIL_PATCH_REPORT_2026-10-03.md

## Reuse / architecture

No new dependency, provider, framework, model, API key, account or paid service.
Use the existing source_acquisition adapter and tests.
This is a bounded safety/evidence-integrity patch, not a new architecture decision.

## Autonomy

D018 Long Goal:
- fix ordinary bugs/tests/refactors autonomously;
- do not stop for routine failures;
- stop only for a real Human Gate/evidence-integrity blocker;
- push origin/main and leave tree clean.

## Acceptance

PASS only if:
- ambiguous rights/location signals can no longer auto-download;
- clearly open/public-domain benchmark cases still work;
- all regressions are green;
- no source-acquisition capability beyond the approved Phase 1 scope is added.

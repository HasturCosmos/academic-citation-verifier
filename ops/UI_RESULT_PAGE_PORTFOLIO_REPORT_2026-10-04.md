# UI Result Page Portfolio Draft Report — 2026-10-04

Status: **IMPLEMENTED + REGRESSION PASS / USER VISUAL ACCEPTANCE PENDING**

Branch: `ui-result-page-v0`
Base: `main@c8a23fd4c547e8f9a5b42a22ef99f86a065ea8f4`
Goal: `ops/UI_RESULT_PAGE_PORTFOLIO_GOAL_2026-10-04.md`

## What changed

This batch stayed inside the authorized result-page UI scope.

- Kept the existing server-rendered HTML/CSS architecture and evidence pipeline.
- Added a restrained academic/product visual hierarchy for the result page.
- Replaced developer-first candidate language with human-readable evidence states.
- Added printed-page-first provenance; PDF sequence pages remain secondary provenance.
- Added a primary-evidence hero only when the accepted backend semantics imply one plausible localized candidate.
- For multiple plausible localized candidates, the page explicitly refuses to force a unique answer.
- Localized candidates can expose original-page highlights; unlocalized candidates can show only clearly labelled unverified page context and never receive fabricated highlights.
- Candidate IDs, raw status, retrieval rank, similarity score and other internals are progressively disclosed under developer detail.
- Evidence-PDF bibliographic identity and secondary-note conflicts are promoted into the normal result hierarchy.
- Copyable citations remain available in the unique-evidence flow.
- No retrieval/model/embedding/provider/OCR/source-acquisition logic was changed.
- The known cand-01 punctuation/localization robustness gap was not fixed or hidden.

## Real Weber Golden Demo UI acceptance evidence

A private preview was rendered from the already-accepted Golden Demo result without changing the original run data.

The real backend result remains `multiple_candidates`:
- 7 localized candidates fall inside the existing plausibility band;
- the human-reviewed correct passage is still candidate rank 5;
- that candidate visibly carries **printed pp.105–106** and **PDF pp.111–112**;
- cand-01 remains unlocalized and is described in human language rather than cosmetically promoted to evidence;
- the 1998 secondary-note claim vs 2021 evidence-PDF identity conflict is visible at result-page level;
- the UI does not special-case rank 5 or use known Golden answer data to manufacture a unique winner.

This is intentionally honest: the Golden Demo proves the system retrieved the correct passage, but the current backend result-state contract does not uniquely select it.

## Regression verification

Final post-change runs:

- MVP + UI probes: **83/83**
- T003 localization probes: **15/15**
- T004 evidence-object probes: **16/16**
- T006 OCR probes: **5/5**
- source-acquisition probes: **106/106**
- Footnote-first probes: **58/58**

All passed. No model/API cost was introduced by this UI work.

New UI probes protect:
- human-readable candidate states;
- printed-page-first provenance;
- PDF sequence page as secondary provenance;
- visible highlight assets only for localized evidence;
- no fabricated highlight for unlocalized candidates;
- edition conflict visibility in both unique and multiple-candidate states;
- raw IDs/scores behind developer disclosure;
- multiple-candidate state never forcing a unique primary answer.

## Visual review

A 1440×1400 real Golden Demo first-screen screenshot was inspected after the final implementation.

The page now presents:
1. overall verification state;
2. evidence-PDF version and bibliographic conflicts;
3. explicit human-confirmation requirement for multiple candidates;
4. compact localized candidate rows with confirmed printed pages;
5. secondary/debug candidates behind progressive disclosure.

The visual style remains a neutral draft. It is **not** declared final brand/portfolio acceptance.

## Scope held

Not added:
- frontend framework;
- new dependency;
- new provider or credential;
- ranking/retrieval change;
- model/embedding change;
- OCR architecture change;
- cand-01 locator tolerance fix;
- whole-app redesign;
- automatic hard-coding of the known Weber answer.

## Human Gate / UNIQUE NEXT

Open the real Weber Golden Demo result page and get the user's visual/product acceptance.

The user should judge:
- whether the page feels clear enough for a non-technical humanities user;
- whether the information hierarchy feels right;
- whether the neutral visual direction is acceptable as the base for the portfolio/demo;
- whether the multiple-candidate confirmation experience now exposes a separate product need.

Do not merge this UI branch to `main` or broaden the product until that review.

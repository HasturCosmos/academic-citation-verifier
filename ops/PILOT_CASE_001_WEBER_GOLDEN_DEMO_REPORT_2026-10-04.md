# Pilot Case 001 — Weber Golden Demo Report

Date: 2026-10-04
Status: **FUNCTIONAL PASS / DEMO-UI NOT ACCEPTED**

## Real inputs

- Secondary paraphrase: the real non-verbatim Weber paraphrase used in Pilot Case 001.
- Recorded secondary footnote: 1998 edition, Feng Keli translation, Foreign Languages Press, p.41.
- Evidence PDF: user-supplied 2021 Shanghai People's Publishing House edition, Yan Kewen translation, ISBN 978-7-208-17140-4.

## Functional result

The normal owned-PDF product path retrieved the corresponding Weber passage without using the preflight answer as a hard-coded page target.

The correct evidence candidate is `cand-05`:
- retrieval rank: 5
- PDF pages: 111-112
- printed pages: 105-106
- localization: located
- original-page highlight images: 2
- model calls: 0
- cost: USD 0.00

The result preserved the edition conflict instead of silently normalizing it:
- secondary note claim: 1998 / Feng Keli / Foreign Languages Press / p.41
- evidence PDF record: 2021 / Yan Kewen / Shanghai People's Publishing House
- evidence citation uses the evidence-PDF edition and pp.105-106.

## Regression evidence

- MVP probes: 76/76
- T003 localization probes: 15/15
- T004 evidence-object probes: 16/16
- T006 OCR probes: 5/5
- source-acquisition probes: 106/106
- Footnote-first probes: 58/58

All passed.

## User-facing findings from live review

The user understood the core evidence result, page provenance, and edition-conflict logic, but did **not** accept the current interface as a demo/portfolio UI.

Specific UX findings to carry into the next stage:

1. `unmatched` is technically correct but opaque. It currently means semantic retrieval produced a candidate chunk, but exact re-localization back to stable PDF geometry failed. The UI must explain this in human language.
2. The candidate list hides confirmed printed-page numbers even when they exist. For the correct candidate, printed pp.105-106 are confirmed and should be prominent; PDF sequence pages should be secondary provenance.
3. A candidate with verified localization should visibly surface original-page evidence and highlight rather than burying them behind debug-style candidate cards.
4. For an `unmatched` candidate, a retrieval page hint may be shown as **unverified page context**, but the UI must not fabricate an exact highlight. If page preview is shown, it must be clearly labeled unverified.
5. Developer/debug vocabulary (`cand-05`, `located`, `unmatched`, raw similarity scores, twelve flat candidate cards) should not dominate the normal UI.
6. The normal result page needs a clear primary-evidence card, edition-conflict explanation, page provenance, original/highlight evidence, and copyable citation; secondary candidates and diagnostics should be progressively disclosed.

## Milestone judgment

The Weber Golden Demo **passes the functional acceptance target** defined by D025.

The current UI is a developer/debug surface and is **not accepted as a portfolio/demo surface**. This does not reopen the functional Golden Demo; it defines the next stage.

## UNIQUE NEXT

Move to product control for **UI / visual / portfolio-demo packaging**, using the user-facing findings above as the starting requirements. No source-provider or credential expansion is justified by this result.

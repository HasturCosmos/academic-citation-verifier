# M3 BASELINE INVENTORY — 2026-10-05

Status: BASELINE INVENTORY COMPLETE / FRESH CASES STILL REQUIRED

This document summarizes existing real-case evidence already present in the repository.
It is not a fresh generalization result and must not be presented as an accuracy claim.

## 1. Existing baseline cases

| Case | Source type | Query type | Retrieval result | Localization / provenance | Cost | What it proves | What it does NOT prove |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pilot Case 001 — Weber | real text-layer PDF, 2021 Chinese edition | real non-verbatim secondary paraphrase + conflicting 1998 footnote | correct passage at retrieval rank 5; 7 plausible localized candidates in current result-state band | correct evidence localized to PDF pp.111–112 / printed pp.105–106; 2 original-page highlights; edition conflict preserved | 0 model calls / USD 0.00 for the accepted run | paraphrase retrieval can reach the correct passage; page provenance and edition conflicts can remain honest | Top-1 reliability; general ranking quality; formal claim-support grading |
| C04 / T003 | real 1800-page text-layer PDF with saved candidate set | historical saved candidates from earlier retrieval | historical gold candidate rank 5; all 10 saved candidates processed | 10/10 uniquely localized; historical gold -> PDF p.109; cross-page candidate -> pp.130–131; highlight geometry verified | 0 model calls / USD 0.00 for localization | page-localization and highlighting work on a very long real PDF, including cross-page spans | fresh retrieval generalization; non-verbatim claim judgment |
| T005B-01 / T006 — Plato Republic | real 459-page image-only Chinese scan | real secondary paraphrase with Book X + Stephanus 605B/607B clues | after RapidOCR, true region is rank 7 (Top-10 hit, Top-1 miss); rank 10 also nearby | true region localized to PDF pp.417–418 with verified highlight; OCR preserves page geometry; canonical margin clues 605/607 recoverable experimentally | 0 model/API calls for retrieval; one-time OCR ≈59.3 min CPU on full 459 pages | scan coverage can be recovered with current optional RapidOCR path; OCR evidence can map back to original pages | ranking quality strong enough for automatic single-answer selection; certified OCR accuracy; formal claim-support grading |

## 2. Existing regression protection

Current accepted product has these reusable automated protections:

- MVP/UI probes: 93/93
- T003 localization: 15/15
- T004 evidence object: 16/16
- T006 OCR: 5/5
- source acquisition: 106/106
- Footnote-first: 58/58

These protect known behavior. They are not substitutes for fresh-case evaluation.

## 3. What the baseline already says

### Confirmed strengths

1. The MVP can retrieve a correct passage even when the secondary wording is not verbatim.
2. Correct passages can be mapped back to real PDF pages and highlighted.
3. Printed-page provenance can be kept separate from PDF sequence pages.
4. Edition conflicts can be preserved rather than silently normalized.
5. Image-only Chinese scans can be made searchable with the existing optional RapidOCR route.
6. The system can fail honestly rather than inventing evidence.

### Confirmed weaknesses / risks

1. Correct evidence may rank mid-list (Weber rank 5; Plato rank 7), so Top-1 cannot currently be treated as automatic truth.
2. The current multiple-candidate UI therefore needs human confirmation by design.
3. OCR full-book preprocessing is slow on CPU for large scans.
4. Exact localization can be punctuation-sensitive in at least one known Weber candidate.
5. Existing reports mostly validate retrieval/localization/evidence mechanics; they do not yet provide a disciplined human gold label for:
   - directly supported;
   - partially supported;
   - unsupported;
   - ambiguous;
   - omitted qualifiers.

## 4. Fresh-case gap

M3 still needs at least **2 genuinely fresh real cases** that were not used to tune the product.

Minimum useful fresh set:

### Fresh Case A — text-layer paraphrase
Required:
- a real secondary quotation/paraphrase;
- the candidate primary PDF;
- preferably no exact copied wording;
- preferably a source not already represented by Weber/C04/Plato.

Purpose:
- measure retrieval rank and page localization on unseen material.

### Fresh Case B — qualifier / ambiguity case
Required:
- a real secondary statement where context, scope, qualification or ambiguity matters;
- the candidate primary PDF.

Purpose:
- test the part of the product that matters academically beyond “find similar text”:
  whether the evidence actually supports the secondary claim and whether important conditions are omitted.

A fresh scan case is optional for this first M3 pass because the scan/OCR path is already heavily exercised by T006.

## 5. Minimum user input still required

For each fresh case, the user only needs to provide:

1. the relevant secondary passage (quote or paraphrase);
2. its footnote / citation if available;
3. the candidate primary PDF.

No manually supplied “correct page” is required before the run.
After the product returns candidates, the user supplies the human gold judgment:
which candidate is actually right and whether the secondary claim is faithful.

## 6. UNIQUE NEXT

Obtain Fresh Case A and Fresh Case B from the user, then run them **without tuning** through the accepted MVP and record the M3 measurements.

Do not change ranking or retrieval before those runs.

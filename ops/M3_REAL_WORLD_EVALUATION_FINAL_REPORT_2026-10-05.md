# M3 REAL-WORLD EVALUATION — FINAL REPORT

Date: 2026-10-05
Status: **M3 FIRST PASS COMPLETE**
Branch: `m3-real-evaluation`
Frozen product base during fresh-case runs: `main@270acaf`

## 1. Executive conclusion

The MVP is **good enough for its current product goal**:

> help a humanities researcher move from a real secondary quotation/paraphrase to a small, traceable set of plausible primary-source passages and original PDF evidence.

It is **not** an automatic proof engine and should not decide final interpretation, evidentiary sufficiency, or academic evaluation on the user's behalf.

The current semantic retrieval quality is satisfactory for this MVP stage.
**Semantic-retrieval optimization is explicitly out of scope.**

The highest-value remaining product gap is **evidence localization robustness on difficult PDF text layers**, because two fresh real cases retrieved relevant passages but failed to map them back to original pages/highlights.

## 2. Product principle confirmed by M3

When multiple passages are genuinely involved:

- show the plausible involved passages;
- keep page/source provenance;
- allow side-by-side human review;
- do not force a unique winner;
- do not silently interpret or evaluate the source for the user.

The product owns:
- discovery;
- retrieval;
- page/source traceability;
- evidence presentation;
- uncertainty disclosure.

The user owns:
- which passages ultimately matter;
- how they should be interpreted;
- how strongly they support a secondary claim;
- the final academic judgment.

Therefore future “which passage is the true one?” gates default to **multi-passage presentation** whenever more than one passage is genuinely plausible.

## 3. Evaluation set

### Known baseline cases

1. **Weber Golden Demo**
   - real non-verbatim paraphrase;
   - real text-layer PDF;
   - edition conflict;
   - correct passage retrieved at rank 5;
   - correct evidence localized to PDF pp.111-112 / printed pp.105-106;
   - 2 original-page highlights;
   - multiple plausible candidates preserved honestly.

2. **C04 / T003**
   - very long real text-layer PDF;
   - 10/10 saved candidates uniquely localized;
   - historical gold candidate localized correctly;
   - cross-page localization verified;
   - highlight geometry verified.

3. **T005B / T006 — Plato scan**
   - real 459-page image-only scan;
   - RapidOCR path;
   - true region retrieved at rank 7;
   - original-page localization/highlight verified;
   - scan pipeline shown to be viable, though CPU preprocessing is slow.

### Fresh real cases

4. **Fresh Case A — Ringer p.94**
   - real secondary paraphrase;
   - footnote cites multiple Weber locations;
   - semantic retrieval reached the relevant source regions;
   - human gold: **PDF pp.127-131 + pp.140-141**;
   - confirms a multi-passage synthesis;
   - product localization failed because the PDF text layer contains compatibility-form / normalization mismatches.

5. **Fresh Case B — Ringer p.89**
   - real secondary paraphrase;
   - footnote cites both `Objektivitait` and `Kritische Studien`;
   - Top-1 reached a highly relevant source region at PDF p.107;
   - Top-10 strongly covered the pp.89-111 cluster;
   - post-run inspection found another important supporting cluster at PDF pp.43-44 not recovered in Top-10;
   - human gold: **PDF pp.43-44 + pp.107-111**;
   - again confirms a multi-passage synthesis;
   - localization failed on the same difficult text layer.

## 4. What the MVP can reliably do now

### A. Retrieve semantically relevant source regions

Across the evaluation set, the MVP repeatedly reaches the right conceptual neighborhood even when:
- wording is non-verbatim;
- the secondary author compresses or paraphrases;
- the correct evidence is not Top-1;
- the secondary paragraph synthesizes multiple original locations.

This is sufficient for the current reference-assistant product bar.

### B. Preserve uncertainty honestly

The MVP does not fabricate:
- page numbers;
- highlights;
- edition identity;
- uniqueness;
- unsupported certainty.

When localization fails, it does not pretend that a page was verified.

### C. Map evidence back to original PDF pages when the text layer is compatible

Weber Golden, C04/T003 and Plato OCR demonstrate that the page-evidence pipeline works:
- page localization;
- cross-page evidence;
- original-page images;
- highlights;
- printed-page/PDF-page separation where available.

### D. Handle both text-layer and scan PDFs

- text-layer PDFs are the default path;
- image-only scans can be processed through the existing optional OCR path;
- OCR results remain subordinate to original-page evidence.

### E. Support a non-technical humanities workflow

The accepted result UI now exposes:
- source PDF;
- bibliographic metadata;
- edition conflicts;
- candidate passages;
- original-page evidence;
- source text;
- copyable citation output.

The product no longer requires the user to inspect developer/debug information.

## 5. What the MVP does NOT reliably do

### A. It does not exhaustively recover every relevant source passage

Fresh Case B proves this clearly:
- one major support cluster was surfaced strongly;
- another important cluster was absent from Top-10.

This is accepted under the current product definition.

### B. It does not guarantee Top-1 is “the answer”

Known real examples:
- Weber Golden correct passage rank 5;
- Plato true region rank 7.

Therefore Top-1 must remain a starting point, not an automatic truth claim.

### C. It does not decide interpretation or evidentiary sufficiency

This is now explicitly **not a product requirement**.

### D. It is not yet robust to all real PDF text-layer encodings

Fresh A and B expose the most important current defect:
- retrieval gets relevant text;
- evidence localization cannot always match that text back to the same PDF;
- Unicode compatibility forms are one confirmed failure mode;
- NFKC alone fixes some candidates but not all.

This defect can cause a misleading final state such as `no_corresponding_passage` even when retrieval has actually reached relevant material.

## 6. Cost and latency

Current accepted local retrieval path:
- 0 model calls;
- USD 0.00 retrieval/model cost in Fresh A and B;
- cold indexing on the 310-page Weber PDF: roughly 64-92 seconds;
- retrieval itself: under 1 second;
- evidence localization: a few seconds.

Known scan path:
- full-book CPU OCR can take close to an hour on a large scan;
- acceptable as an optional path for the current MVP, not an optimization target now.

## 7. M3 verdict

### Portfolio/demo readiness

**YES — with explicit product positioning.**

The MVP is ready to demonstrate as:

> a humanities citation-verification assistant that retrieves plausible primary-source passages, preserves source/page evidence, exposes ambiguity, and helps users verify secondary citations faster.

Do **not** market it as:
- automatic citation truth verification;
- exhaustive source recovery;
- guaranteed Top-1 correctness;
- automated scholarly interpretation.

### Product quality bar

For the current MVP, success means:

> reliably narrow a large primary source to a small set of plausible, traceable passages that a researcher can inspect.

It does not mean:

> automatically determine the one true passage and the correct scholarly interpretation.

## 8. Highest-value next product gap

**Evidence localization robustness for difficult PDF text layers.**

Why this is next:
- it affects a core promise already present in the product UI: page + highlight;
- it failed in both fresh real cases;
- semantic retrieval was already useful in those same cases;
- fixing localization does not require changing product positioning or ranking;
- it is a bounded engineering problem.

Scope of the next fix should remain narrow:
- improve normalization/matching between retrieved candidate text and PDF text-layer extraction;
- preserve evidence honesty;
- do not alter semantic retrieval;
- do not hard-code Fresh A/B pages;
- keep existing regression suites green.

## 9. Explicitly deferred

Not in the next stage:
- semantic-retrieval optimization;
- rerankers;
- query expansion;
- LLM reranking;
- exhaustive multi-document source search;
- PMS;
- mobile UI;
- broad provider expansion;
- automatic scholarly interpretation.

## 10. UNIQUE NEXT

Open a bounded **localization-robustness Goal**.

Goal:
> candidates already retrieved from a text-layer PDF should robustly map back to their original page(s) despite Unicode compatibility forms and common extraction-normalization differences, without changing retrieval/ranking.

Acceptance should be tested first on Fresh A/B, then against all existing regression suites.

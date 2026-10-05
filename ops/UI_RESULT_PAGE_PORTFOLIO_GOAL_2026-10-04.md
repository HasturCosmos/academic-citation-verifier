# UI RESULT PAGE PORTFOLIO DEMO GOAL — 2026-10-04

Status: AUTHORIZED UI STAGE / IMPLEMENTATION NOT YET ACCEPTED

Base: `main@c8a23fd4c547e8f9a5b42a22ef99f86a065ea8f4`

## CURRENT

The Weber Golden Demo is a functional PASS. The current normal result surface is still a developer/debug UI and is not accepted as a portfolio/demo surface.

This Goal starts the UI stage with the smallest high-value slice: **redesign the result page first**. Do not redesign the whole application in this batch.

## USER OUTCOME

Within a few seconds of opening a successful result, a non-technical humanities user should be able to answer:

1. Did the product find evidence that can be checked on the original PDF page?
2. What is the corresponding Chinese primary-source text?
3. Where exactly is it: confirmed printed page first, PDF sequence page second?
4. What edition supplied the evidence, and does it conflict with the secondary footnote?
5. What citation can I copy?

The page should feel like a citation-verification product, not a retrieval debugger.

## REUSE FIRST

Reuse the existing server-rendered HTML/CSS and current evidence pipeline in `tools/mvp_app.py`.

Do **not** introduce React/Vue/Streamlit/Tailwind or another frontend framework for this Goal.
Do **not** add a new UI dependency unless a concrete blocker is demonstrated.

Existing data already contains the needed evidence fields:
- candidate status;
- original/display text;
- printed page numbers when confirmed;
- PDF page numbers;
- original/highlight image refs;
- bibliographic metadata + per-field provenance;
- metadata conflicts;
- copyable footnote/reference citations;
- result-state classification.

## INFORMATION ARCHITECTURE

### Successful unique-evidence state

When the backend result state is `evidence_found`, the normal page should lead with one **primary evidence** story.

The primary evidence must be derived from the same already-accepted result-state semantics, not invented by visual order:
- consider only `located` candidates with highlight evidence;
- use the same plausibility rule already used by `mvp.classify_result_state`;
- only when that accepted state implies one plausible located candidate may the UI present it as the primary evidence.

Primary evidence block, in this order:

1. Human-readable verdict.
2. Prominent confirmed **printed page** when available.
3. Secondary provenance: PDF sequence page.
4. Corresponding Chinese original text with copy action.
5. Original-page highlight images visible without opening a debug accordion.
6. Edition / bibliographic identity of the evidence PDF.
7. Edition conflict, when present, stated in plain Chinese:
   - what the secondary note claimed;
   - what the evidence PDF actually is;
   - which edition the generated evidence citation uses.
8. Copyable footnote/reference citation.

### Multiple plausible evidence state

When the backend state is `multiple_candidates`, do not visually force a single answer.
Lead with a clear message that several passages remain plausible and need user confirmation.
Show the plausible localized candidates compactly; keep other candidates behind progressive disclosure.

### No reliable passage / insufficient source

Use a clean failure/next-step state.
Do not render a wall of candidate cards as if they were answers.

## HUMAN-READABLE CANDIDATE STATES

Developer labels must not dominate normal UI.

Normal-language meaning:

- `located` → “已定位到原页，可回查”
- `unmatched` → “检索到相近文本，但未能稳定定位原页”
- `ambiguous` → “找到文本，但原页位置不唯一，需要人工核对”
- `needs_ocr` → “当前页面缺少可稳定定位的文本，需要 OCR / 人工核对”

Raw labels, candidate IDs, retrieval ranks, similarity scores and internal diagnostics belong in developer/detail disclosure.

## PAGE PROVENANCE CONTRACT

- If printed pages are confirmed, make them primary: e.g. “印刷页 105–106”.
- PDF sequence pages remain visible but secondary: e.g. “PDF 顺序页 111–112”.
- Never display a PDF sequence page as though it were a printed page.
- An unlocalized candidate may show a retrieval-page hint only as **unverified page context**.
- Never fabricate an exact highlight for an unlocalized candidate.

## SECONDARY CANDIDATES

Do not show twelve flat debug cards by default.

Normal view:
- primary/plausible evidence first;
- a compact “其他检索候选” disclosure after the main evidence;
- each alternative shows a short excerpt + human-readable state;
- original technical metadata is available under a deeper developer disclosure.

## VISUAL DIRECTION FOR THIS DRAFT

This batch may establish a conservative neutral academic/product baseline:
- clear typography and whitespace;
- restrained cards/borders;
- strong evidence hierarchy;
- highlight imagery given real visual weight;
- responsive at narrow widths.

This is a **draft implementation baseline**, not the final brand/art direction.
Final visual/brand acceptance remains a Human Gate.

## SCOPE BOUNDARY

In scope:
- `tools/mvp_app.py` result-page rendering and CSS needed for the result page;
- minimal helper functions required only to express the accepted result-state semantics;
- tests/probes that protect the new result-page behavior;
- documentation/status updates for this UI Goal.

Out of scope:
- retrieval ranking changes;
- embedding/model changes;
- source acquisition/provider changes;
- credentials;
- OCR architecture changes;
- fixing the cand-01 punctuation-tolerant locator gap;
- changing the Golden Demo functional judgment;
- homepage / identity / finder full redesign in this batch;
- new frontend framework;
- hiding or silently normalizing bibliographic conflicts.

## GOLDEN DEMO ACCEPTANCE

Use the existing Weber Golden Demo as the primary live acceptance case.

The redesigned result must make these facts easy to understand:
- corresponding passage is supported by a verified localized candidate;
- confirmed printed pages: 105–106;
- PDF sequence pages: 111–112;
- two original/highlight page images;
- secondary note claims 1998 / Feng Keli / Foreign Languages Press / p.41;
- evidence PDF is 2021 / Yan Kewen / Shanghai People's Publishing House;
- evidence citation uses the evidence-PDF edition;
- candidate/debug internals are not the visual center of the page.

The existing cand-01 localization gap must remain honestly represented as unverified rather than being cosmetically converted into evidence.

## REGRESSION ACCEPTANCE

Implementation is not accepted until:
- existing functional suites stay green;
- new UI probes cover at least:
  - human-readable candidate-state labels;
  - printed-page-first provenance;
  - PDF page kept as secondary provenance;
  - localized candidate exposes highlight assets in normal view;
  - unlocalized candidate does not fabricate highlight;
  - edition conflict remains visible;
  - debug IDs/scores are progressively disclosed;
  - multiple-candidate state does not force a single answer.

## HUMAN GATE

After a working draft is rendered with the real Golden Demo:
- user reviews the visual direction and result-page comprehension;
- only then may the design be called portfolio/demo accepted.

## UNIQUE NEXT

Implement this bounded result-page UI Goal on this branch, run regressions, render the real Weber Golden Demo, and stop for user visual acceptance. Do not expand the product.

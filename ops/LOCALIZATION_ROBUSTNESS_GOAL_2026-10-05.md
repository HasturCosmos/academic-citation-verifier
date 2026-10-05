# LOCALIZATION ROBUSTNESS GOAL — 2026-10-05

Status: ACTIVE
Stage: post-M3 bounded engineering fix
Base: M3-complete branch, no retrieval changes allowed

## 1. Problem

M3 Fresh Case A and B both show the same product failure mode:

- semantic retrieval reaches relevant text from a real text-layer PDF;
- the evidence locator then fails to match that retrieved text back to the same PDF;
- result state becomes `no_corresponding_passage`;
- no original-page highlight is emitted.

The source PDF contains Unicode compatibility-form / extraction differences.
NFKC normalization alone restores exact matches for some relevant candidates, proving a real normalization gap.

## 2. Product boundary

This Goal is **not** a semantic-retrieval project.

Do not change:
- embeddings;
- ranking;
- reranking;
- query construction;
- chunking;
- k;
- PaperQA retrieval behavior;
- model/provider architecture;
- source acquisition.

The product remains a reference / verification assistant.
When multiple passages are plausibly involved, surface them; do not force a unique academic judgment.

## 3. Reuse-first decision

Reuse and harden the existing locator:
`tools/t003_evidence_localize.py`.

Current locator already provides:
- page-hint window search;
- whole-PDF fallback;
- normalized->original index mapping;
- exact/ambiguous/unmatched states;
- cross-page fragments;
- character geometry;
- original-page highlighting.

Do not replace this architecture.

## 4. Required fix

Improve normalization/matching so a retrieved candidate can map back to its PDF text layer despite common extraction differences.

Minimum required behavior:
1. Unicode compatibility normalization (NFKC or equivalent) with a correct normalized-character -> original-entry mapping.
2. Existing whitespace/invisible-character tolerance remains.
3. Do not delete arbitrary CJK/digits merely to force a match.
4. If a second, carefully bounded tolerant pass is needed for punctuation variants, it must:
   - preserve traceability to original character geometry;
   - never guess when several possible matches exist;
   - return `ambiguous` rather than fabricate a unique highlight.
5. Cross-page mapping must remain correct.
6. No known Fresh A/B page numbers or candidate text may be hard-coded.

## 5. Acceptance

### Fresh real cases
On the unchanged Fresh A and B saved candidates:
- at least one genuinely relevant candidate from each case must become `located`;
- original PDF page number(s) must be correct;
- highlight image(s) must be emitted;
- no false unique match may be introduced.

Stretch target:
- materially more than one relevant candidate per case localizes if the normalization differences are safely resolvable.

### Regression
Keep green:
- MVP/UI probes;
- T003;
- T004;
- T006;
- source acquisition;
- Footnote-first.

### Evidence honesty
- ambiguous stays ambiguous;
- unmatched stays unmatched when no defensible full-text mapping exists;
- no guessed page/highlight.

## 6. Tool routing

Recommended implementation:
- Model: DeepSeek V4.1 Flash
- Reasoning: Medium
- Mode: Goal
- Why: bounded, low-risk, regression-testable engineering fix.

Escalate to GPT6 High only if:
- maintaining normalized->geometry mapping becomes non-trivial;
- current PDFium extraction semantics create a hard correctness bug;
- repeated bounded attempts fail.

## 7. UNIQUE NEXT

Implement the smallest normalization hardening in the existing locator, add focused regression probes for Unicode compatibility forms, replay Fresh A/B, then run all six regression suites.

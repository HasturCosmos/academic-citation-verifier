# DECISIONS

## D001 — Product before curriculum

Status: confirmed

Learning is just-in-time and serves the current development obstacle.
Do not restore the old generic AI-learning curriculum.

## D002 — V1 scope is intentionally narrow

Status: superseded by D010 on 2026-10-01

V1 starts from:
secondary quotation/paraphrase + candidate primary PDF.

It does not start from whole-web source discovery.

## D003 — Evidence traceability is mandatory

Status: confirmed

The product must prioritize raw source evidence, page provenance, context, and human review.
Generated summaries alone are not sufficient evidence.

## D004 — Research First

Status: confirmed

Before reinventing reusable functionality, quickly evaluate maintained open-source alternatives.

## D005 — M1 will not start from a hand-built RAG stack

Status: confirmed

Research First found mature components for parsing, retrieval, reranking, and provenance.

## D006 — Experiment PaperQA2 first

Status: confirmed

PaperQA2 is the first M1 baseline because it minimizes custom engineering.
MinerU-based architecture is a fallback, not a parallel first experiment.

## D007 — GitHub is the shared state bus

Status: confirmed

Chat / Work / Codex should synchronize through repository state instead of requiring the user to manually copy large prompts/results between surfaces.

## D008 — Cost discipline

Status: confirmed

Use the lowest sufficient model/reasoning mode and avoid Goal / Ultra / multi-agent usage unless the expected benefit clearly justifies the extra quota/token cost.

## D009 — Human gate remains for key decisions

Status: confirmed

Automation may handle low-risk execution and bookkeeping, but the user confirms product-scope changes, durable architecture choices, and milestone acceptance.


## D010 — Product definition V0.1

Status: confirmed

The user confirmed `ops/PRODUCT_V0_1.md` on 2026-10-01.

Key durable points:
- product name: 二流文科生的二手文献;
- input may be pasted text, PDF, or image/photo, plus an optional free-form hints field;
- footnotes and user hints are fallible clues, not authoritative facts;
- scope is author-agnostic; coverage is determined by currently accessible full-text sources;
- core delivery is Chinese primary-source evidence: original text + original-page screenshot/highlight + page + basic copyable citation;
- multiple plausible passages and multiple Chinese editions are shown rather than forced into a single winner;
- results use progressive disclosure;
- MVP does not need universal source acquisition before the first runnable demo;
- long interpretive verification is deferred/on-demand to control cost.

This decision supersedes the earlier candidate-primary-PDF-only product scope in D002 while preserving that workflow as a useful retrieval subproblem and evaluation route.


## D011 — T003 milestone accepted

Status: confirmed

On 2026-10-01 the user explicitly accepted T003.

Accepted evidence:
- the lightweight pypdfium2/Pillow evidence-localization route works on the C04 text-native PDF case;
- 10/10 saved candidates localized, gold on PDF page 109, cross-page evidence on 130/131, 15/15 regression probes passed;
- the evidence layer can remain separate from retrieval and emit explicit failure states without guessing.

Boundary:
this acceptance validates T003 and authorizes reuse of this route for the next reversible vertical-slice task. It does not yet finalize the entire product architecture, prove OCR/scanned-document coverage, or accept the full MVP.


## D012 — T004 milestone accepted

Status: confirmed

On 2026-10-01 the user explicitly accepted T004.

Accepted evidence:
- the first backend vertical slice starts from the real secondary-source query and reaches multiple candidate primary passages, exact PDF-page geometry, highlighted original-page images, copyable original text, and metadata-honest basic citation output;
- all 12 T004 acceptance criteria passed;
- T004 regression probes passed 16/16 and T003 regression probes passed 15/15;
- the historical gold passage surfaced and resolved to PDF page 109;
- the workflow preserves multiple candidates and does not substitute PDF sequence pages for unknown printed book pages.

Boundary:
this acceptance validates the C04 end-to-end backend slice. It does not yet establish cross-document generalization, OCR/scanned-document coverage, external source acquisition, final ranking behavior, final architecture, or full MVP acceptance.

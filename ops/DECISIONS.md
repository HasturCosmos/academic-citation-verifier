# DECISIONS

## D001 — Product before curriculum

Status: confirmed

Learning is just-in-time and serves the current development obstacle.
Do not restore the old generic AI-learning curriculum.

## D002 — V1 scope is intentionally narrow

Status: confirmed

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

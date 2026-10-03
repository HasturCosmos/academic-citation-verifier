# PROJECT_STATE

Last updated: 2026-10-03 (MVP COMPLETE + intake patch + source-acquisition Phase 1 complete + guardrail hardening complete + footnote-first V0.2 simplification COMPLETE)

## Project

二流文科生的二手文献引用助手.

## Current phase

Gate 0 product definition: CLOSED.

Historical MVP milestone D019 remains accepted. The active product definition is **Footnote-first V0.2** (`ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md`, D022/D023).

Implementation commit `9c929012` is **not yet accepted as pilot-ready**. Control-room review on 2026-10-03 found bounded state-continuity defects that the self-verification probes missed. No new architecture is required.

Active fix brief: `ops/FOOTNOTE_FIRST_ACCEPTANCE_FIX_GOAL_2026-10-03.md`.

## Current status

### What passed in control-room review

- The normal UI visibly implements the three V0.2 blocks.
- Footnote parsing is a distinct deterministic component and cited work vs containing publication are modelled separately.
- The normal no-PDF lookup is routed through parsed/confirmed identity rather than a free-standing broad search.
- Technical/demo controls are collapsed out of the normal flow.
- The existing evidence/highlight pipeline remains reused rather than replaced.
- Codex reported regressions green at delivery: MVP 70/70, T003 15/15, T004 16/16, T006 5/5, source acquisition 98/98, footnote-first 16/16. GitHub has no commit status / Actions run for `9c929012`, so those executions are recorded delivery evidence, not an independent CI rerun by control-room review.

### Blocking acceptance findings

1. **Secondary-page upload is dropped on the normal `/identify` path.** The page advertises secondary screenshot/PDF input, but `/identify` only handles `footnote_file`; `secondary_file` is not extracted there.
2. **Footnote-image upload is dropped on the owned-PDF `/extract` path.** The direct-PDF route therefore loses the main navigation clue when the note is supplied as a screenshot.
3. **Confirmed bibliographic identity is not carried end-to-end.** `id_*` edits are used to build the `/find` query but are not preserved through `/use_found` or the no-PDF -> owned-PDF continuation, and they do not feed citation metadata. The UI can therefore say “identity kept” while a later result still has no confirmed citation metadata.
4. **The insufficient-clue retry cannot actually accept a new clue.** Its form resubmits hidden unchanged values.

These are acceptance blockers because they break advertised V0.2 user paths; they are small, reversible product defects rather than a reason to reopen the architecture.

### UNIQUE NEXT

Execute `ops/FOOTNOTE_FIRST_ACCEPTANCE_FIX_GOAL_2026-10-03.md`, rerun all regressions plus the new path-level probes, then return to control-room review.

Do **not** start another architecture expansion or real-user pilot before that re-review.

## T004 end-to-end backend slice (executed 2026-10-01)

- Brief: `ops/T004_END_TO_END_BACKEND_SLICE.md`. Report: `ops/T004_BACKEND_SLICE_REPORT.md`.
- New code: `tools/t004_backend_slice.py` (live retrieval mode, offline candidate mode, `--recheck` acceptance re-evaluation) and `tools/t004_regression_probes.py` (16 zero-cost probes). No new dependency, no upstream modification, no parser/OCR/architecture change.
- Acceptance run: one command starting from the real 38-character historical query -> `Docs.aadd` + `Docs.aquery` with the pinned T001 settings (CLI agent never used) -> 10 ranked candidates -> T003 localization at 144 DPI -> evidence objects. Parse+embed+add 400.25 s, query 19.14 s, evidence 9.59 s.
- Result: 10/10 candidates `located` with unique full matches; historical gold candidate at **retrieval rank 2**, resolving to **PDF page 109**; 11 highlighted + 11 original-page images; raw 400-character chunk text preserved as `original_text`; every candidate carries an explicit status, warnings and unresolved fields.
- Cost: 11 model calls, 5722 prompt / 9308 completion tokens (`deepseek-flash`), **$0.0128862**. Zero Docling/MinerU/OCR cost; no new paid stage beyond reproducing the T001-style retrieval flow.
- Metadata honesty: the citation shells contain only caller-supplied confirmed metadata; the printed book page is unresolved, so no page number appears in any citation and `pdf_page_numbers` is never substituted. PaperQA2's inferred docname is not used (explicit docname/citation are passed, which also removes T001's useless citation-inference call).
- Verification: 12/12 acceptance criteria in `acceptance.json`; T004 probes 16/16 (statuses, image rules, cross-page, wrong-hint fallback, schema, candidate preservation, PDF-vs-printed page, citation rules, `needs_ocr`, gold-tolerance bound/false positives); T003 probes re-run 15/15.
- Integrity: `C04.pdf` sha256 `d3e3b068…b48c1` and the T001 results JSON sha256 `68238b48…c335` re-verified unchanged; PDF mtime untouched. All private text/images remain under the git-ignored `data/private/C04/t004/`.
- Boundary: `ambiguous`, `unmatched` and `needs_ocr` are proven by probes on synthetic fixtures, not yet by a real case. This PASS is a feasibility result for C04 and is not a durable architecture decision or M1 acceptance.

## T003 C04 highlight experiment (executed 2026-10-01)

- Brief: `ops/T003_C04_HIGHLIGHT_EXPERIMENT.md`. Report: `ops/T003_C04_EVIDENCE_REPORT.md`.
- New dependencies (project `.venv`): `pypdfium2` 5.13.0, `Pillow` 12.3.0. No model download, no Docling/MinerU/OCR.
- New code: `tools/t003_evidence_localize.py` (thin, retrieval-independent localization/evidence adapter) and `tools/t003_regression_probes.py` (probes + synthetic fixtures).
- Result: all 10 saved T001 candidates `located` with a unique full match in the 1800-page PDF; the historical gold candidate (rank 5) localizes to PDF page 109; the cross-page candidate produces one fragment on page 130 and one on page 131; 11 evidence fragments, 140 highlight runs, 11 highlighted page images at 144 DPI; 5.96 s wall clock; 0 model/API calls, $0.00.
- Verification: 15/15 regression probes pass (whitespace/line-wrap, repeated text -> ambiguous, missing text -> unmatched, cross-page, rotations 0/90/180/270, cropped page, no text layer -> needs_ocr, wrong stored hint -> whole-PDF fallback, and a whitespace rewrite of the stored gold candidate). All 11 highlighted screenshots were inspected visually.
- Integrity: `C04.pdf` sha256 `d3e3b068…b48c1` and the T001 results JSON sha256 `68238b48…c335` were captured before the run and re-verified unchanged afterwards; the PDF mtime is untouched.
- Boundary: this validates the evidence-delivery slice on C04 only. It is not a durable architecture decision and not M1 acceptance; both remain human decisions.

## T002 architecture plan (saved 2026-10-01)

- Full plan: `ops/T002_ARCHITECTURE_PLAN.md`, preserving the previously generated plan and its sources; the save note distinguishes the original planning snapshot from the current repository state.
- Recommendation, not a confirmed durable architecture decision: retain PaperQA2 retrieval and add a pypdfium2/Pillow evidence layer; use independently preserved Docling provenance as the first fallback. MinerU and OCR are deferred unless a demonstrated failure requires them.
- User selected whole-candidate highlighting for the first C04 experiment, not automatic shortest-sentence selection.
- Planning-time read-only check: all 10 saved T001 candidates uniquely match their cached page text after whitespace removal, including the candidate spanning PDF pages 130–131; cache size/mtime matches the current PDF. This does not validate geometric coordinates or screenshots.
- Proposed next experiment reuses the saved candidates to validate coordinates and original-page highlighting with zero new model/API calls. It has NOT started; no geometry/highlight acceptance result exists.
- Current authorization covers saving the plan, updating ops state, and commit/push only. No product code, dependency installation, or new experiment is included; durable decisions remain unchanged.

## M1-E1 run environment (prepared 2026-09-30)

- Interpreter: project-local `.venv` created with `py -3.11` → Python 3.11.9 (`D:\Python311`), i.e. deliberately not the machine-default 3.14.
- Package: `paper-qa` **2026.8.12**, installed the upstream way via `pip install "paper-qa>=5"`.
- Reproducibility anchors: litellm 1.84.1, lmi (fhlmi) 1.0.7, aviary (fhaviary) 0.37.0, pydantic 2.13.5, pypdf 6.19.0, tantivy 0.26.2.
- Verified: `import paperqa` OK; `pqa --help` OK (exit 0); C04 PDF readable from `data/private/C04/` (1800 pages, page 109 extracts, gold phrase present).
- `.gitignore` now additionally covers `.venv/`, `.pqa/`, `.env*`, Python caches; `data/private/` was already ignored.

## M1-E1 minimal config (identified, not yet confirmed)

DeepSeek path confirmed by read-only inspection of the installed LiteLLM 1.84.1:

- `deepseek/deepseek-chat` resolves to provider `deepseek`, reads `DEEPSEEK_API_KEY`, default api_base `https://api.deepseek.com/beta`;
- deepseek-chat advertises function calling / response schema / tool choice, so it fits PaperQA2 tool and JSON prompts;
- deepseek-reasoner has no function calling.

Still open before the first real baseline run:

- embedding: PaperQA2's default `text-embedding-3-small` is an OpenAI API embedding and DeepSeek exposes no embeddings endpoint, so an explicit local choice is required (`st-<model>` via the `local` extra plus a model download, or `sparse`). Not installed, not decided.
- parsing defaults would call OpenAI: `parsing.multimodal=ON_WITH_ENRICHMENT` with `enrichment_llm=gpt-4o-2024-11-20`, and `parsing.use_doc_details=true` can trigger an LLM citation prompt. These must be turned off or redirected for a DeepSeek-only run.
- indexing scope: the default `paper_directory` is the repository root with recursion on; it should be narrowed to `data/private/C04`.
- PQA home: `pqa_directory()` always mkdirs `~/.pqa`, which the sandboxed session refuses. Use `PQA_HOME=<repo>` (creates the already-ignored repo-local `.pqa/`) or run unsandboxed.
- `DEEPSEEK_API_KEY` exists in the Codex session environment but is not set at Windows User/Machine scope, so a baseline run must inject it (session env, or a git-ignored `.env`, which LiteLLM auto-loads).

## M1-E1 run mechanics (verified 2026-10-01)

- Tracked baseline settings as executed: `.pqa/settings/m1e1_c04.json` uses `embedding: st-BAAI/bge-small-zh-v1.5`, `deepseek/deepseek-flash` for llm/summary_llm/agent_llm, `temperature 0`, `parsing.use_doc_details=false`, `parsing.multimodal=false`, `reader_config {chunk_chars 400, overlap 100}`, `answer.evidence_k 10`, `agent.index {name m1e1_c04, paper_directory data/private/C04/pqa_corpus}`. Earlier values (`sparse`, then the 128-token MiniLM, then `bge-m3`) are superseded — see the compatibility finding and baseline result sections below.
- Corpus isolation: the candidate corpus is `data/private/C04/pqa_corpus/C04.pdf`, a hardlink to the original PDF (same 18.1 MB inode). The gold-case markdown stays outside `paper_directory` so it cannot be indexed and leak the answer.
- PQA home: `pqa_directory()` unconditionally creates `${PQA_HOME}/.pqa/<name>` (else `~/.pqa`), which the managed sandbox refuses. All runs must set `PQA_HOME` to the repo root; `.pqa/indexes/` and `.pqa/cache/` are git-ignored while `.pqa/settings/*.json` is tracked.
- Network: the managed sandbox has no egress; the formal baseline was therefore executed with authorized network escalation. T001 is complete.
- Indexing cost note: `Docs.aadd` performs one citation-inference LLM call per file when no citation is supplied, even with `use_doc_details=false`. One PDF therefore adds one short call to the run.

## M1-E1 parsing/retrieval evidence (2026-10-01, zero-API)

- `paper-qa-pypdf` parses the C04 PDF cleanly: 1800 pages, 1,650,866 chars after whitespace removal, median 981 chars/page (min 37, max 1860), 15 pages under 50 chars (front/back matter), ~124-131 s for the full parse. No scanned-page failure observed.
- Chunk provenance is page-range granularity, not per-page: labels look like `C04.pdf pages 108-109`, and a chunk carries no internal page map. Granularity tracks `chunk_chars`: 5000/250 → 370 chunks with the gold region labelled 106-112; 2500/250 → 780 chunks, 108-111; 1200/200 → 1754 chunks, 108-109. `chunk_chars=1200, overlap=200` is therefore the provisional setting for M1 page provenance.
- Zero-API recall pre-check using upstream components only (`Docs.aadd_texts` + `Docs.retrieve_texts`, `embedding: sparse`, `k=10`, chunking 1200/200): embedding+index took 0.7 s for 1754 chunks and the gold passage chunk ranked **4th**, i.e. inside Top-5, and the chunk covering PDF page 109 is that same hit. This is the pre-rerank retrieval stage only; the LLM evidence/answer stages can still reorder or drop it.
- Caveat for evaluation: on PDF page 109 the gold sentence is interrupted by 4 inserted characters (Unicode categories Nd,Lo,Lo,Lo), i.e. an annotation/number baked into the text layer. Exact substring matching will fail, so M1 scoring must use normalization or page-based matching rather than byte-exact comparison.
- Diagnostic tool: `tools/m1e1_parse_probe.py` reads private files at runtime, prints only aggregates and Unicode categories, and caches parsed pages under `.pqa/cache/` (ignored).

## M1-E1 embedding/chunk compatibility finding (2026-10-01, zero-API)

The approved local embedding cannot see most of each chunk:

- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` has `max_seq_length = 128` tokens, while 1200-char C04 chunks measure a median of 790 tokens (max 906): **100% of chunks are truncated**, so the vector for each chunk describes only its first ~16%.
- With 500-char chunks the median is 330 tokens and with 300-char chunks 199 tokens, so truncation persists until chunks shrink to roughly 120 Chinese characters.

Retrieval-stage matrix (upstream `Docs.aadd_texts` + `Docs.retrieve_texts`, `k=10`, MMR lambda 1.0, the historical noisy C04 query; no LLM involved):

| embedding | chunk_chars/overlap | chunks | gold chunk rank |
| --- | --- | --- | --- |
| `sparse` | 1200 / 200 | 1754 | 4 (page-range 108-109) |
| MiniLM (approved) | 1200 / 200 | 1754 | not in top-10 |
| MiniLM (approved) | 120 / 20 | 17533 | 7 (page 109 exactly) |
| hybrid MiniLM + sparse | 1200 / 200 | 1754 | not in top-10 |

Interpretation: PaperQA2's retrieval design assumes a long-context embedding (its own default is an 8191-token OpenAI model). Substituting a 128-token model breaks chunk retrieval; this is a configuration mismatch, not evidence against PaperQA2 itself. MiniLM also reaches only rank 7 even without truncation, and 120-char chunks destroy the surrounding context that M1 requires.

This incompatibility was resolved for T001 by switching to `BAAI/bge-small-zh-v1.5` with 400-character chunks. The finding is retained as experiment history.

## M1-E1 first baseline result (2026-10-01, one paid run)

Pinned configuration: `embedding: st-BAAI/bge-small-zh-v1.5`, `reader_config {chunk_chars 400, overlap 100}`, DeepSeek `deepseek/deepseek-flash` for llm/summary_llm/agent_llm, `parsing.use_doc_details=false`, `parsing.multimodal=false`, `evidence_k 10`.

Entry point: PaperQA2 core API (`Docs.aadd` + `Docs.aquery`) rather than the CLI agent, because the agent's file-level `paper_search` uses a tantivy tokenizer that cannot match Chinese. No PaperQA2 source was modified; the adapter is `tools/m1e1_baseline_run.py`.

Measured (raw result kept in `data/private/C04/results/`, not in the repository):

- parse + embed + add of the 1800-page PDF: 420 s (5844 chunks, all within the model's 512-token window);
- query time: 21 s; answer length: 619 characters;
- 10 ranked contexts returned, each the **raw 400-character chunk text** (not a model summary), each labelled with its page range;
- the gold passage chunk is at **rank 5** (`pages 109-109`) → M1 success condition "gold in Top-5" is met at the boundary; Top-1 and Top-3 are missed;
- context relevance scores by rank: 7, 10, 5, 4, 10, 8, 9, 10, 10, 4;
- cost: **$0.01206** (LiteLLM-computed), tokens 5668 prompt / 8635 completion.

M1-E1 success conditions:

1. gold in Top-5 — MET at rank 5 (boundary);
2. correct PDF page preserved — MET (`pages 109-109` label);
3. raw original text surfaced — MET (raw chunk text, not a summary);
4. sufficient local context — partial (400-character chunk; page-boundary context only);
5. Top-1/Top-3/Top-5 rank recorded — MET (Top-1 miss, Top-3 miss, Top-5 hit);
6. integration/code modification amount — MET: no upstream modification, one ~80-line adapter script needed to bypass the Chinese-incompatible file search;
7. model/API cost recorded — MET ($0.01206, 5668/8635 tokens).

Observations to carry into T002:

- the zero-cost retrieval pre-check had the gold chunk at rank 2 with 400-char chunks and rank 1 with 300-char chunks, so chunk size is the main tunable left;
- the inferred citation/docname came out as `Rejoice2026`, i.e. the citation-inference call produced a useless document name for this Chinese book;
- the upstream CLI agent path is not usable for this case without an adapter, which is itself relevant to the "is PaperQA2 sufficient" decision.

## Confirmed M1 goal

Given:
- one real academic PDF;
- one real secondary-source quotation/paraphrase;

return:
- top candidate original passages;
- raw source text (not only model summaries);
- PDF page provenance;
- enough surrounding context for human verification.

## First baseline experiment

M1-E1 uses historical case C04.

Known gold facts:
- source work: Max Weber, *Economy and Society* Chinese translation by Yan Kewen, Shanghai People's Publishing House, 2019;
- historical test PDF: combined two-volume PDF, 1800 PDF pages;
- query contains a small omission/noise;
- gold original passage is on PDF page 109 (1-based);
- gold text contains the phrase equivalent to “他人的表现，并据此作为行动进程的取向”.

The C04 PDF and gold-case artifact are now ready in local private data (`data/private/C04/`), verified: 1800 PDF pages total and page 109 readable.

## M1-E1 minimum success conditions

1. Gold passage appears in Top-5.
2. Correct PDF page can be preserved/recovered.
3. Raw original text can be surfaced.
4. Sufficient local context can be recovered.
5. Record Top-1/Top-3/Top-5 rank.
6. Record integration/code modification amount.
7. Record actual API/model cost where measurable.

## Candidate technical routes

Primary baseline:
- PaperQA2-first.

Fallback only if evidence justifies it:
- MinerU 4 + existing hybrid retrieval;
- Docling / PaddleOCR / Marker as parsing fallbacks where appropriate.

## Known boundaries

Not in the current MVP:
- PMS;
- automatic literature review writing;
- automatic paper writing;
- unnecessary multi-agent systems;
- universal/full-coverage literature acquisition before the first demo;
- broad production UI.

Automatic source discovery/acquisition is part of the product direction only through currently available/connected source adapters; lack of a source is a valid MVP failure state.

## Context health

GREEN for repository state.

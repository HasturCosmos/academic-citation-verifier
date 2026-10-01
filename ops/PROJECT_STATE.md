# PROJECT_STATE

Last updated: 2026-09-30

## Project

AI academic citation verification assistant.

## Current phase

M1 — evidence retrieval.

## Current status

- New clean Project created in ChatGPT.
- Project Instructions v1.1 installed.
- Migration baseline created and accepted.
- Research First completed.
- GitHub connector confirmed working.
- This repository is the shared state bus for Chat / Work / Codex.
- No product code has been written here yet.
- M1-E1 PaperQA2 run environment is prepared locally (see below). PaperQA2 is installed as a package in the project `.venv`; no upstream source was cloned or modified.
- No model/API call has been made yet; no model cost has been incurred.

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

## M1-E1 run mechanics (verified 2026-10-01, still no paid call)

- Tracked baseline settings: `.pqa/settings/m1e1_c04.json` currently still use `embedding: sparse` together with DeepSeek for llm/summary_llm/agent_llm, `temperature 0`, `parsing.use_doc_details=false`, `parsing.multimodal=false`, `reader_config {chunk_chars 1200, overlap 200}`, `answer.evidence_k 10`, `agent.index {name m1e1_c04, paper_directory data/private/C04/pqa_corpus}`. The user-approved SentenceTransformer (`st-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) has not yet been swapped into the tracked settings.
- Corpus isolation: the candidate corpus is `data/private/C04/pqa_corpus/C04.pdf`, a hardlink to the original PDF (same 18.1 MB inode). The gold-case markdown stays outside `paper_directory` so it cannot be indexed and leak the answer.
- PQA home: `pqa_directory()` unconditionally creates `${PQA_HOME}/.pqa/<name>` (else `~/.pqa`), which the managed sandbox refuses. All runs must set `PQA_HOME` to the repo root; `.pqa/indexes/` and `.pqa/cache/` are git-ignored while `.pqa/settings/*.json` is tracked.
- Network: the sandbox has no egress. `pqa index` failed at `Cannot connect to host api.deepseek.com:443`, so the formal baseline still needs escalated (unsandboxed) execution; no request reached DeepSeek and nothing was billed. Therefore T001 is not yet complete.
- Indexing cost note: `Docs.aadd` performs one citation-inference LLM call per file when no citation is supplied, even with `use_doc_details=false`. One PDF therefore adds one short call to the run.

## M1-E1 parsing/retrieval evidence (2026-10-01, zero-API)

- `paper-qa-pypdf` parses the C04 PDF cleanly: 1800 pages, 1,650,866 chars after whitespace removal, median 981 chars/page (min 37, max 1860), 15 pages under 50 chars (front/back matter), ~124-131 s for the full parse. No scanned-page failure observed.
- Chunk provenance is page-range granularity, not per-page: labels look like `C04.pdf pages 108-109`, and a chunk carries no internal page map. Granularity tracks `chunk_chars`: 5000/250 → 370 chunks with the gold region labelled 106-112; 2500/250 → 780 chunks, 108-111; 1200/200 → 1754 chunks, 108-109. `chunk_chars=1200, overlap=200` is therefore the provisional setting for M1 page provenance.
- Zero-API recall pre-check using upstream components only (`Docs.aadd_texts` + `Docs.retrieve_texts`, `embedding: sparse`, `k=10`, chunking 1200/200): embedding+index took 0.7 s for 1754 chunks and the gold passage chunk ranked **4th**, i.e. inside Top-5, and the chunk covering PDF page 109 is that same hit. This is the pre-rerank retrieval stage only; the LLM evidence/answer stages can still reorder or drop it.
- Caveat for evaluation: on PDF page 109 the gold sentence is interrupted by 4 inserted characters (Unicode categories Nd,Lo,Lo,Lo), i.e. an annotation/number baked into the text layer. Exact substring matching will fail, so M1 scoring must use normalization or page-based matching rather than byte-exact comparison.
- Diagnostic tool: `tools/m1e1_parse_probe.py` reads private files at runtime, prints only aggregates and Unicode categories, and caches parsed pages under `.pqa/cache/` (ignored).

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

Not in current scope:
- PMS;
- automatic whole-web literature discovery;
- automatic literature review writing;
- automatic paper writing;
- unnecessary multi-agent systems;
- broad production UI.

## Context health

GREEN for repository state.

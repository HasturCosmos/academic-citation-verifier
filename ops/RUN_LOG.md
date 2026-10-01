# RUN_LOG

## 2026-09-30 — Repository control plane initialized

Actor: ChatGPT via GitHub connector

Actions:
- created AGENTS.md;
- created PROJECT_STATE.md;
- created TASK_QUEUE.md;
- created DECISIONS.md;
- created RUN_LOG.md.

Purpose:
establish GitHub as the shared state bus for Chat / Work / Codex and reduce manual copy-paste handoffs.

No product code, dependency installation, PaperQA2 clone, or Codex execution was performed.

Next active task:
T001 — prepare and execute the M1-E1 PaperQA2 baseline after the C04 PDF/gold case are available to the runtime and the live Codex configuration is inspected.

## 2026-09-30 — C04 local test material acceptance

Actor: Codex (local)

Actions:
- verified `data/private/C04/` contains the C04 combined two-volume PDF and `M1-E1_C04_gold_case.md`;
- confirmed the PDF is readable with 1800 pages and page 109 extracts successfully;
- confirmed the gold-case file includes the raw query, gold original text, gold PDF page 109, and the M1-E1 minimum success conditions;
- confirmed `data/private/` remains Git-ignored and neither test file is tracked.

No PaperQA2 clone, dependency install, model call, or product-code change was performed.

## 2026-09-30 — Codex configuration blocker cleared

Actor: ChatGPT via GitHub connector

Actions:
- reconciled repository task state with the completed Codex read-only configuration check;
- recorded that the active Codex provider/model configuration has been inspected and verified;
- removed the stale blocker claiming that live Codex configuration had not yet been recorded.

No product code or dependency changes were made.

## 2026-09-30 — Project-level reasoning effort set to medium

Actor: Codex (local)

Actions:
- created `.codex/config.toml` containing only `model_reasoning_effort = "medium"`;
- confirmed via resolved Codex config that the project default effort is medium and is sourced from the project `.codex` layer;
- confirmed `model`, `model_provider`, `base_url`, and `wire_api` are still inherited from the global user config;
- global Codex config was not modified, and no provider, model, base_url, env_key, or secret was copied into the repository.

## 2026-09-30 — T001 PaperQA2 run environment prepared (no model calls)

Actor: Codex (local)

Scope: environment preparation only, per the explicit instruction not to run the formal C04 model experiment tonight. No LLM/embedding API call was made and no model cost was incurred.

Actions:
- created a project-local `.venv` with `py -3.11` (Python 3.11.9 from `D:\Python311`), deliberately not the machine-default Python 3.14;
- extended `.gitignore` to cover `.venv/`, `.pqa/`, `.env`/`.env.*`, Python caches, and OS noise, keeping the existing `data/private/` rule;
- confirmed via `git check-ignore -v` that `.venv/` and `data/private/C04/M1-E1_C04_gold_case.md` are both ignored;
- upgraded pip in the venv, then installed upstream-style with `pip install "paper-qa>=5"`;
- verified the install offline-capable ways only: `import paperqa`, `pqa --help`, and reading the C04 PDF through the venv interpreter.

Recorded versions:
- Python 3.11.9 (venv); `paper-qa` 2026.8.12 (CalVer); `paper-qa-pypdf` 2026.8.12;
- litellm 1.84.1; lmi (fhlmi) 1.0.7; aviary (fhaviary) 0.37.0; pydantic 2.13.5; pypdf 6.19.0; tantivy 0.26.2; openai 2.54.0.

Verification results:
- `import paperqa` succeeds (`.venv\Lib\site-packages\paperqa\__init__.py`);
- `pqa --help` succeeds with exit code 0;
- C04 PDF still readable from `data/private/C04/`: 1800 pages, page 109 extracts 920 characters, and the gold phrase fragment is present on page 109;
- no PaperQA2 source was cloned or modified, no custom RAG was built, and MinerU was not introduced.

Read-only DeepSeek/LiteLLM findings (no calls made):
- LiteLLM registers a native `deepseek` provider: `deepseek/deepseek-chat` maps to provider `deepseek`, reads `DEEPSEEK_API_KEY`, and defaults to `https://api.deepseek.com/beta` (override via `DEEPSEEK_API_BASE`);
- `deepseek-chat` advertises function calling, response schema, and tool choice, so PaperQA2's tool/JSON prompts are structurally supported; `deepseek-reasoner` does not support function calling;
- LiteLLM auto-loads a repo-local `.env` on import, which is one clean way to inject the key without committing it.

Open items blocking the first real baseline run:
- embedding choice: the PaperQA2 default `text-embedding-3-small` is an OpenAI API embedding and DeepSeek has no embeddings endpoint, so a local option is required (`st-<model>` via the `local` extra plus a model download, or `sparse`); nothing extra was installed tonight;
- OpenAI-dependent parsing defaults must be pinned off or redirected (`parsing.multimodal=ON_WITH_ENRICHMENT`, `enrichment_llm=gpt-4o-2024-11-20`, `parsing.use_doc_details`);
- `paper_directory` should be narrowed to `data/private/C04` instead of the repo root;
- `pqa_directory()` unconditionally mkdirs `~/.pqa`, which the sandboxed session denies, so runs need `PQA_HOME=<repo>` or unsandboxed execution;
- `DEEPSEEK_API_KEY` is present in the Codex session environment but not set at Windows User/Machine scope, so the baseline process must receive it explicitly;
- user authorization for baseline model spend and its cap.

Note on secrets: no key value was written to any file, and nothing under `.venv/`, `.pqa/`, or `data/private/` is tracked by Git.

## 2026-10-01 — T001 read-only baseline configuration review

Actor: ChatGPT via GitHub connector

Scope: no local install, no model call, no product-code change.

Findings:
- upstream PaperQA2 supports local SentenceTransformer embeddings through the `local` extra and `st-<model>` configuration;
- upstream tests contain an explicit note that `embedding="sparse"` was too weak for a retrieval test, so using sparse only to avoid a download would make M1-E1 a poor-quality baseline;
- because C04 is Chinese, the current lowest-cost candidate for the first run is `st-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, a 50-language SentenceTransformer that does not require query/passage prefixes;
- current DeepSeek API documentation (2026-09-10 model update) uses `deepseek-flash`; repository notes still reference `deepseek/deepseek-chat`, so the installed LiteLLM 1.84.1 must receive one no-cost local compatibility check before the paid run.

Gate:
- embedding choice remains a proposed experiment configuration, not a durable architecture decision;
- no paid baseline call should be made until the user approves the configuration and spending cap.


## 2026-10-01 — User gate cleared for T001 first paid baseline

Actor: User, recorded by ChatGPT via GitHub connector

Authorizations:
- approved the local multilingual SentenceTransformer install/model download for M1-E1;
- approved proceeding to the first DeepSeek-backed C04 baseline;
- no hard RMB spending cap for this first experiment.

Cost constraint still in force:
- use the lowest sufficient configuration;
- do not make redundant model calls;
- do not add Goal / Ultra / multi-agent parallelism;
- record actual model/API spend after the run.

Next executable step:
- local Codex should continue T001 from repository state: install/download the approved local embedding, pin the minimal PaperQA2 settings, perform the no-cost model-name compatibility check, then run exactly one formal C04 baseline and write results back to ops/.

## 2026-10-01 — T001 continued: config pinned, parsing/retrieval evidence collected (zero-API)

Actor: Codex (local)

Scope: environment and configuration work only. No LLM/embedding call was completed; the single attempted network call failed at connect time, so nothing was sent to DeepSeek and nothing was billed.

Actions:
- created the tracked baseline settings file `.pqa/settings/m1e1_c04.json` (DeepSeek llm/summary_llm/agent_llm, `embedding: sparse`, temperature 0, `parsing.use_doc_details=false`, `parsing.multimodal=false`, `reader_config 1200/200`, `evidence_k 10`, index name `m1e1_c04`, `paper_directory data/private/C04/pqa_corpus`);
- verified it loads with `pqa -s m1e1_c04 view` (exit 0);
- isolated the candidate corpus by hardlinking the PDF to `data/private/C04/pqa_corpus/C04.pdf`, so the gold-case markdown can never be indexed as a candidate source;
- added `tools/m1e1_parse_probe.py`, a zero-model-call parsing/chunking probe that reads private files at runtime and prints only aggregates and Unicode categories;
- narrowed `.gitignore` from `.pqa/` to `.pqa/indexes/` plus `.pqa/cache/`, keeping `.pqa/settings/*.json` trackable while index and parse-cache artifacts stay ignored.

Findings recorded:
- the sandbox has no network egress (`pqa index` failed at `Cannot connect to host api.deepseek.com:443` before any request was sent), so the paid run must be executed with escalation;
- `pqa_directory()` always mkdirs `${PQA_HOME}/.pqa/<name>` and falls back to `~/.pqa`, which the managed sandbox refuses, so every run must set `PQA_HOME` to the repo root;
- `Docs.aadd` makes one citation-inference LLM call per file when no citation is given, even with `use_doc_details=false`; one PDF adds one short call;
- `paper-qa-pypdf` parses C04 cleanly: 1800 pages, 1,650,866 chars, median 981 chars/page, 15 pages under 50 chars, 124-131 s per full parse;
- chunk provenance is a page *range* label (`C04.pdf pages 108-109`) with no internal page map; granularity follows `chunk_chars` — 5000/250 gives 106-112, 2500/250 gives 108-111, 1200/200 gives 108-109;
- zero-API recall pre-check with upstream components (`Docs.aadd_texts` + `Docs.retrieve_texts`, sparse embedding, k=10, chunks 1200/200): the gold chunk ranked 4th of 10, i.e. inside Top-5, and it is the chunk covering page 109 (embedding+index 0.7 s for 1754 chunks);
- the gold sentence on page 109 is interrupted by 4 inserted characters (categories Nd,Lo,Lo,Lo), so exact substring scoring will fail and M1 must score with normalization or page matching.

Cost: zero. Only local CPU was used (one 131 s PDF parse, then cached under the ignored `.pqa/cache/`).

Note: the `sparse` embedding used for this pre-check was afterwards superseded by the user-approved local SentenceTransformer (`st-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`); the sparse numbers are kept as the cheap lower-bound reference.

## 2026-10-01 — T001 blocker found: approved embedding cannot see the chunks

Actor: Codex (local)

Scope: authorized install and zero-API measurement. The paid C04 baseline was deliberately **not** run, because a zero-cost check showed the approved configuration cannot retrieve the gold chunk at all.

Actions:
- installed `paper-qa[local]` → sentence-transformers 6.1.0 + torch 2.14.1 (plus transformers 5.18.0, scikit-learn 1.9.1, scipy 1.17.1);
- downloaded `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` into the Hugging Face cache (`~/.cache/huggingface`), verified it loads through paperqa's `st-` factory (384-dim);
- re-ran the zero-API retrieval pre-check with the approved embedding and with a hybrid variant.

Measured (retrieval stage only: upstream `Docs.aadd_texts` + `Docs.retrieve_texts`, k=10, MMR lambda 1.0, the historical noisy C04 query):

| embedding | chunk_chars/overlap | chunks | gold chunk rank |
| --- | --- | --- | --- |
| `sparse` | 1200 / 200 | 1754 | 4 |
| MiniLM (approved) | 1200 / 200 | 1754 | not in top-10 |
| MiniLM (approved) | 120 / 20 | 17533 | 7 |
| hybrid MiniLM + sparse | 1200 / 200 | 1754 | not in top-10 |

Cause:
- MiniLM's `max_seq_length` is 128 tokens, but 1200-char chunks measure median 790 tokens (max 906) and 500-char chunks median 330: every chunk is truncated, so each embedding describes only a small prefix of its text;
- PaperQA2's design assumes a long-context embedding (its own default is an 8191-token OpenAI model), so this is a configuration mismatch rather than evidence about PaperQA2;
- even without truncation MiniLM reaches only rank 7, and 120-char chunks leave no usable surrounding context for M1.

Cost: zero API spend. All work was local (one 57 s embedding pass for dense, one 223 s pass for the 120-char configuration) plus two authorized downloads.

Gate: the paid baseline stays on hold until the embedding/chunking decision is confirmed. Options on the table: (a) long-context multilingual embedding such as `st-BAAI/bge-small-zh-v1.5` (512 tokens, ~95 MB, Chinese-tuned) or `st-BAAI/bge-m3` (8192 tokens, ~2.2 GB, no prefixes) with 1200-char chunks kept; (b) keep MiniLM with ~120-char chunks (known weak); (c) fall back to `sparse` at 1200 chars (rank 4).

## 2026-10-01 — T001 first paid C04 baseline executed and measured

Actor: Codex (local)

Scope: exactly one paid baseline run, as authorized. No PaperQA2 source was modified, no custom RAG was built, no MinerU was introduced.

Configuration work before the run:
- downloaded `BAAI/bge-m3` (8192-token window, verified 1024-dim) but abandoned it for this run: a single full-corpus CPU embedding pass ran over 75 minutes without completing, which is impractical when the paid run must embed the same corpus again;
- switched to `BAAI/bge-small-zh-v1.5` (512-token window, ~95 MB, Chinese-tuned). Zero-cost pre-check: 400-char chunks → gold chunk at rank 2 with zero truncated chunks; 300-char chunks → rank 1;
- pinned `.pqa/settings/m1e1_c04.json` to `st-BAAI/bge-small-zh-v1.5`, `chunk_chars 400`, `overlap 100`, and `deepseek/deepseek-flash` for all three LLM roles;
- replaced the CLI-agent entry point with PaperQA2's core API (`Docs.aadd` + `Docs.aquery`) in `tools/m1e1_baseline_run.py`, because the agent's file-level `paper_search` searches a tantivy index whose tokenizer turns Chinese sentences into single tokens, so a Chinese query can never match.

Model-name check (no token cost): a `GET /models` call returned HTTP 200 with exactly `deepseek-flash` and `deepseek-v4-pro`, so `deepseek-chat` is no longer available; LiteLLM resolves `deepseek/deepseek-flash` to the native deepseek provider. The repository note from 2026-09-30 that claimed `deepseek/deepseek-chat` was correct is superseded.

Result of the single run (raw output in `data/private/C04/results/m1e1_c04_20261001-113927.json`):

- aadd (parse + embed 5844 chunks): 420 s; query: 21 s; answer: 619 characters;
- 10 ranked contexts, each the raw 400-character chunk text with a page-range label;
- gold passage chunk at **rank 5**, labelled `pages 109-109` → Top-5 success condition is MET at the boundary, Top-1 and Top-3 missed;
- context scores by rank: 7, 10, 5, 4, 10, 8, 9, 10, 10, 4;
- cost $0.01206 (LiteLLM-computed), 5668 prompt / 8635 completion tokens;
- the citation-inference call produced the docname `Rejoice2026`, i.e. useless metadata for this Chinese book.

Cost: one paid run, $0.01206. Everything else this turn was local CPU or free metadata calls.

Next: T002 — decide whether PaperQA2 is sufficient for M1 given rank 5 / boundary Top-5 with a raw-text, page-labelled evidence path, plus the two adapted components (entry point and embedding) and the weak citation metadata.


## 2026-10-01 — Gate 0 product definition accepted; T001 reviewed

Actor: User + ChatGPT via GitHub connector

Product:
- user explicitly confirmed PRODUCT_V0_1;
- product scope now starts from secondary-source text/PDF/image plus optional fallible hints, and aims to return corresponding Chinese primary-source evidence from currently accessible source adapters;
- the old candidate-primary-PDF-only scope is retained as a retrieval subproblem, not the whole product boundary.

T001 acceptance:
- Codex completed the first paid PaperQA2 C04 baseline;
- gold passage reached rank 5 (Top-5 boundary), exact page label was preserved, raw source text was surfaced, and cost was $0.01206;
- Chinese CLI-agent search was unusable, but a thin adapter using PaperQA2 core API succeeded without modifying upstream source;
- citation metadata inference was poor (`Rejoice2026`);
- bge-m3 was CPU-impractical in the local environment, while bge-small-zh-v1.5 with 400-char chunks was practical.

Acceptance:
T001 is accepted as a successful technical spike for the within-PDF retrieval subproblem, with caveats. It is not accepted as the final product architecture.

Next:
T002 — short Reuse Scan + PRODUCT_V0_1 fit review, then decide which PaperQA2 components to retain.

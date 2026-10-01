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

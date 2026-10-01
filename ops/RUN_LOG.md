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


## 2026-10-01 — T002 preliminary Reuse Scan after PRODUCT_V0_1

Actor: ChatGPT

Scope: read-only external scan; no local install, no model/API execution.

Findings:
- PaperQA2 is still actively maintained (latest release line includes v2026.08.12) and now supports model-based PDF readers including Docling and nemotron-parse, plus page numbers, images/tables, DPI, reusable indexes, and manual `Docs` API access.
- The completed T001 baseline tested the default pypdf-style text path plus a thin `Docs.aadd`/`Docs.aquery` adapter; it did NOT yet test PaperQA2's geometry-aware/model-based reader options.
- Docling exposes item-level provenance including page number, bounding box, and character span, which maps directly to PRODUCT_V0_1's screenshot/highlight requirement.
- MinerU also exposes structured layout/box output and OCR-oriented parsing; PaddleOCR remains a mature OCR fallback/component rather than something to reimplement.
- Therefore T001 does not justify discarding PaperQA2, but neither does it justify adopting PaperQA2 as the whole product architecture.

Next technical question for T002:
compare the smallest geometry-preserving route that can reuse PaperQA2 retrieval against a simpler parser + retrieval composition on the same C04 case. The acceptance target is PRODUCT_V0_1 evidence delivery (candidate text + exact page + highlightable coordinates), not generic RAG answer quality.

## 2026-10-01 — T002 architecture plan saved; implementation remains gated

Actor: Codex (local), at the user's explicit save/update/commit/push request.

Scope: documentation only. Fast-forwarded the clean local main checkout from `8ece1f3` to `e60ecc2` before saving, preserving the shared product definition and state. Saved the full previously generated plan to `ops/T002_ARCHITECTURE_PLAN.md` with a note identifying its historical snapshot and the user-requested filename; synchronized PROJECT_STATE and TASK_QUEUE. DECISIONS was not changed.

Plan recommendation: retain PaperQA2 retrieval, add pypdfium2/Pillow for coordinates and original-page highlights, and reserve Docling with separately preserved provenance as the first fallback. The plan includes source links, layer interfaces, failure states, one C04 experiment, acceptance criteria, effort estimate, and human gates.

Evidence reused from the prior planning turn: all 10 saved T001 candidates uniquely matched their cached page text after whitespace removal, including the candidate spanning PDF pages 130–131; PDF size/mtime matched the parse cache. These are text-localization checks, not geometric or screenshot validation. The user selected whole-candidate highlighting; the gold rank 5 remains a historical T001 result.

Runtime inspection for this save operation: local config specifies `gpt-6-astra` with `high` reasoning and no explicit model_provider entry; no historical DeepSeek-backed Codex runtime assumption was made. No model setting was changed, and no Goal or multi-agent mode was used.

Validation: documentation diff/whitespace and plan completeness checks only. No product code was changed, no dependencies installed, and no experiment or new model/API call was run. Additional experiment/API spend: zero.

Gate: plan drafting is complete and saved for review; saving/pushing is not architecture acceptance or authorization to start the next experiment. Await the user's next instruction.


## 2026-10-01 — T002 plan reviewed and accepted for experiment

Actor: ChatGPT

Review:
- the saved T002 plan is internally consistent with PRODUCT_V0_1 and the T001 evidence;
- it reuses PaperQA2 only where T001 demonstrated value, while separating page geometry/highlighting from retrieval;
- pypdfium2/Pillow is the smallest reversible next test for text-native C04 PDFs;
- Docling remains a targeted fallback rather than a parallel stack;
- the plan correctly avoids ranking optimization, OCR, UI, source acquisition, and new model/API spend at this stage.

Acceptance:
T002 is accepted as the basis for a reversible experiment only. No final architecture selection is made.

Next:
T003 — execute the saved-candidate -> exact page geometry -> original-page highlight experiment under `ops/T003_C04_HIGHLIGHT_EXPERIMENT.md`.


## 2026-10-01 — T003 C04 highlight experiment executed (PASS)

Actor: Codex (local), on the user's `/goal` instruction to execute T003 strictly against its acceptance criteria, fix ordinary implementation/test problems autonomously, stop expansion if the primary route failed, then update repository state, commit/push and report the commit SHA with a PASS/FAIL summary.

Repository sync: local `main` was 4 commits behind `origin/main` (T003 brief and state updates had been pushed from another environment); fast-forwarded to `9fdbb3c` before starting. No local work was lost.

Scope: the evidence-delivery slice only — candidate passage -> exact PDF page -> character geometry -> original-page render -> highlighted image + machine-readable record. No retrieval rerun, no Docling/MinerU/OCR, no UI, no ranking work.

Dependencies added (project `.venv`, Python 3.11.9): `pypdfium2` 5.13.0, `Pillow` 12.3.0. No model download.

Implementation: `tools/t003_evidence_localize.py` and `tools/t003_regression_probes.py`. Normalization removes whitespace and invisible format characters only and keeps a mapping back to original character positions; the stored page range is a fallible hint (window search, then whole-document fallback); statuses are `located / ambiguous / unmatched / needs_ocr`; only `located` candidates produce geometry; cross-page candidates are split per page; pixel coordinates come from `FPDF_PageToDevice` with the renderer's exact arguments (crop and rotation handled by PDFium, no assumed y-flip); highlights are per-character boxes grouped into text runs; pages render at 144 DPI.

Result: 10/10 stored candidates `located` with a unique full match in the 1800-page PDF; the historical gold candidate (rank 5) localizes to **PDF page 109**; the cross-page candidate yields fragments on pages **130 and 131**; 11 fragments, 140 highlight runs, 11 highlighted images; 5.96 s wall clock; 0 model/API calls, $0.00. All 11 highlighted screenshots plus one unmarked original were inspected visually: every highlight follows the candidate text line by line, includes superscript markers inside the span, and hides no unrelated body text.

Regression probes: 15/15 PASS — whitespace exact/stripped/tabs+newlines/padded, repeated text -> `ambiguous` with no highlight, missing text -> `unmatched` with no highlight, cross-page -> one fragment per page, rotations 0/90/180/270, CropBox smaller than MediaBox, no text layer -> `needs_ocr`, wrong stored hint -> whole-PDF fallback with `hint_confirmed=false`, and a whitespace rewrite of the stored gold candidate (same page, complete 374/374 span).

Two implementation defects were found by the acceptance/probe checks and fixed: (1) line grouping measured overlap against a line's accumulated extent, so an entire paragraph collapsed into one block rectangle; (2) the first pixel conversion used `get_size()` with a rotation swap plus a manual y-flip, which was wrong for cropped and rotated pages — replaced by PDFium's own `FPDF_PageToDevice` (verified against synthetic fixtures: ink density inside the highlight ~0.23–0.33 for all four rotations, versus 0.00 for the naive MediaBox y-flip).

Documented limitations (no failure class hit): PDFium returns rotated-page text in display order, so a passage whose lines are reordered by the rotation is `unmatched` (individual lines still localize correctly); `rank-04`'s stored candidate text contains page 130's running footer, which is therefore highlighted faithfully; whole-candidate highlighting extends beyond the shortest matching sentence by the confirmed experiment preference.

Integrity: `C04.pdf` sha256 `d3e3b0687c70fb8db9179d40b2d666ed3536bcfa14da3602a78fdc5c791b48c1` and the T001 results JSON sha256 `68238b48e348b148457e59409e84a8003ff244e8b4ee2a144b4a9461e8bbc335` were captured before the run and re-verified unchanged afterwards (PDF mtime 2026-09-15 14:00:37 untouched). Private text, images and records stay under the git-ignored `data/private/C04/evidence/`.

Additional experiment/API spend: zero.

Gate: PASS is a feasibility result for C04 only. Durable architecture selection and M1 acceptance remain user decisions. Next candidate T004 is proposed in TASK_QUEUE and is not authorized by this run.


## 2026-10-01 — User accepted T003; T004 activated

Actor: User + ChatGPT

Gate:
the user explicitly accepted the T003 milestone.

Interpretation:
- T003's lightweight evidence-localization route is accepted for reuse in the next reversible experiment;
- this is not a final product-architecture acceptance and does not imply OCR/source-acquisition coverage.

Reuse Scan:
the next task can be built almost entirely from current project capabilities: the existing PaperQA2 core retrieval path from T001 plus the pypdfium2/Pillow evidence layer from T003. No new external subsystem is needed for the first backend vertical slice.

Next:
T004 — `ops/T004_END_TO_END_BACKEND_SLICE.md`: start from the real secondary-source query, run candidate retrieval, localize/highlight candidates, and emit structured evidence/citation objects.


## 2026-10-01 — T004 end-to-end backend vertical slice executed (PASS 12/12)

Actor: Codex (local), on the user's `/goal` instruction to execute T004 strictly against its acceptance criteria, fix ordinary implementation/test problems autonomously, stop expansion if the route required an architecture change, then update repository state, commit/push and report the commit SHA with PASS/FAIL.

Repository sync: local `main` was 5 commits behind `origin/main` (T003 acceptance and T004 activation had been pushed from another surface); after GitHub egress returned, `git fetch origin main` + `git merge --ff-only origin/main` fast-forwarded `c28edb1` → `e394fe4` with no local work lost.

Model rule: live Codex runtime inspected before the work — provider `custom` (DeepSeek), model `deepseek-flash`, reasoning `low`; no historical model assumption was reused. No Goal/Ultra mode and no multi-agent delegation was used for this task, per D008.

Scope: connect the proven layers into one backend loop — real secondary-source query → PaperQA2 core retrieval → T003 evidence localization → product evidence objects with citation shells. New code: `tools/t004_backend_slice.py` and `tools/t004_regression_probes.py`. No dependency added, no upstream modification, no Docling/MinerU/OCR, no retrieval-architecture change, no UI.

Acceptance run (one command, live mode): `PQA_HOME=<repo> .venv/Scripts/python.exe tools/t004_backend_slice.py --t003-probe-summary ... --out-dir data/private/C04/t004/run`. It starts from the real historical 38-character T001 query read from the gold case at run time (the noisy wording was not repaired) and uses `Docs.aadd` + `Docs.aquery` with the pinned T001 settings; the CLI agent is never used. Timings: parse+embed+add 400.25 s, query 19.14 s, evidence+render 9.59 s.

Result: 10 candidates, 10/10 `located` with unique full matches; the historical gold passage is candidate `cand-02` at retrieval **rank 2** and its evidence resolves to **PDF page 109**; 11 highlighted + 11 original-page PNGs at 144 DPI, every fragment `geometry_ok` (0 clipped runs, ink density ≥ 0.065 per run); every candidate keeps its raw 400-character chunk text as copyable `original_text`.

Acceptance criteria: **12/12 PASS**, machine-readable in `data/private/C04/t004/run/acceptance.json` and reproducible with `--recheck <run_dir>` (no model call). Highlights: criterion 2 (core API, `cli_agent_used=false`), criterion 4 (gold → page 109, tolerating exactly 1 inserted text-layer character of category `Nd`), criterion 9 (citation shells byte-equal to shells rebuilt from the same confirmed metadata, so a PDF page can never appear where a printed page belongs), criterion 10 (`git ls-files data/private` empty; every image ref under `data/private/`).

Metadata honesty (product rule): the workflow passes an explicit docname/citation from the caller's confirmed record, so PaperQA2's inferred docname (historically `Rejoice2026`) is not used at all and the useless per-file citation-inference LLM call is avoided. Citation shells emitted: `[德]马克思·韦伯：《经济与社会（第一卷）》，阎克文译，上海：上海人民出版社，2019年。` and `[德]马克思·韦伯.经济与社会（第一卷）[M].阎克文译.上海:上海人民出版社,2019.` — no page segment, because the printed book page is unconfirmed; `printed_page` and `printed_page_numbers` stay in `unresolved_fields`.

Regression: new T004 probes **16/16 PASS** (statuses reach the product object, images only for `located`, cross-page two images, wrong-hint whole-document fallback, ambiguous/unmatched warnings, evidence-object schema, candidate preservation, PDF-vs-printed page separation, citation page-only-when-confirmed, unresolved-field listing, missing translator not invented, no shell without author/title, `needs_ocr` on a no-text-layer page, gold-tolerance acceptance/bound/false-positive guard). T003's probes were re-run unchanged: **15/15 PASS**. Both suites are zero-cost.

Cost: **11 model calls**, 5722 prompt / 9308 completion tokens (`deepseek-flash`), **$0.0128862** — the same order as the authorized T001 baseline and with no new paid stage beyond reproducing that retrieval flow. No Docling/MinerU/OCR spend.

Integrity: `C04.pdf` sha256 `d3e3b0687c70fb8db9179d40b2d666ed3536bcfa14da3602a78fdc5c791b48c1` and the T001 results JSON sha256 `68238b48e348b148457e59409e84a8003ff244e8b4ee2a144b4a9461e8bbc335` were captured before the run and re-verified unchanged afterwards (PDF mtime 2026-09-15 14:00:37 untouched). All private text, images and records remain under the git-ignored `data/private/C04/t004/`.

Observations carried forward: (1) retrieval returns the same 10 chunk pages as T001 but the LLM evidence reranking reorders them (gold rank 5 in T001, rank 2 here, rank 3 in the embedding-only diagnostic stage), so rank is not yet a stable product signal; (2) candidate `cand-09` (pages 130–131) still carries the PDF's running footer line inside its stored 400-character text, the known page-furniture backlog item; (3) only `located` was exercised by the live case — `ambiguous`, `unmatched` and `needs_ocr` are proven by probes on synthetic fixtures.

Gate: T004 PASS is a feasibility result for the C04 vertical slice and authorizes no further expansion. Durable architecture selection and M1 acceptance remain user decisions. Proposed follow-ups are listed in TASK_QUEUE (real failure-state coverage first, ranking-stability question second).


## 2026-10-01 — T004 accepted; clean-chat handoff point reached

Actor: User + ChatGPT

The user explicitly accepted T004.

The product-control chat has now completed Gate 0 product definition plus T001-T004. GitHub contains the confirmed product definition, decisions, task state, reports, and acceptance history. The next stage is real-case generalization before UI expansion.

This is a safe handoff point: a new ChatGPT control-room chat can resume from GitHub state without manual copy/paste from the old chat.


## 2026-10-01 — T005A evidence-layer reuse benchmark: KEEP_CURRENT

Actor: Codex

Task: the sole NEXT in TASK_QUEUE — benchmark `docushell/ethos` against the custom T003 pypdfium2/Pillow evidence layer before writing more evidence code.

Method: read-only inspection of Ethos at `main` `1101f0b6b06557b144769ed82a6ebaa9afb34127` (2026-09-07, v0.6.0 publication closeout) via the GitHub connector: README, docs/execution-status.md, docs/CLAIMS.md, schemas/README.md, pyproject.toml, rust-toolchain.toml, the v0.6.0 release manifest and asset list, the v0.6.0 closeout record, and the python/ and bindings/ trees. Local environment checked before any install. No PaperQA2 rerun, no model/API calls, no dependency installed, no upstream checkout.

Result: KEEP_CURRENT. Phase 1 found no Windows-runnable Ethos path: v0.6.0 publishes only macOS arm64 and Linux x64 CLI archives, the Python wheel is a thin wrapper around a caller-provided `ethos` CLI, and the npm package vendors only those two platforms. Ethos's own closeout states the run "produced a verify-only Windows candidate, which was deliberately withheld because Windows packaged artifacts remain a blocked lane". Local machine has no rustc/cargo/rustup, no make, and no WSL distribution. The T005A guardrail requires stopping before installing a system-wide Rust toolchain solely for Ethos, so Phase 2 (runtime comparison) was deliberately not run.

Capability audit: Ethos is a deterministic citation-verification/grounding layer over an already-parsed document representation (native Ethos JSON, an OpenDataLoader-style adapter, or caller-written Grounding JSON). It matches our `needs_ocr` intent with `ocr_required`, but it is literal-matching (a paraphrase is explicitly not grounded), has no semantic truth judgement, and does not perform passage discovery or localization from a fallible page hint. Its v0.6.0 cross-page "adjacent-element join" is a different semantic that fails the gate closed via `semantic_unverified`, not one candidate split into per-page fragments. Its determinism contract explicitly excludes exact page boxes and rendered images from the cross-platform guarantee. Net: zero T003/T004 code would be removed, and adoption would add a toolchain, a subprocess boundary, and a second document representation.

Recorded for the future, not adopted: Ethos's `schemas/normalization-vectors.json` and `normalization-vectors-unicode-compat-v1.json` as an Apache-2.0 conformance reference, and the `capability_limits` / `semantic_unverified` fail-closed honesty pattern. Re-open triggers recorded in the report (an official Windows artifact or packaged native binding; a shift to claim-vs-source verification over already-parsed documents; explicit ambiguity/cross-page support).

Bookkeeping: while updating state, removed a duplicated `D012 — T004 milestone accepted` block in `ops/DECISIONS.md` (two identical-numbered entries had landed); the surviving block is the first, longer one, and no decision content changed.

Cost: 0 model calls, $0.00. No private source material modified. C04 artifacts untouched.

Gate: T005A answers one component question and authorizes no expansion. It is not a durable architecture decision and not M1 acceptance. Next work is real-case generalization with a genuinely new academic case exercising an honest failure state.


## 2026-10-01 — T005A control-room review passed

Actor: ChatGPT product control

Independent GitHub review accepted the T005A task result **KEEP_CURRENT**. The review checked the report, latest commit scope, task/state synchronization, and spot-checked Ethos upstream documentation: Windows has no packaged CLI artifact, the Python package wraps a caller-provided CLI, and Ethos explicitly does not provide semantic judgement/OCR. Commit `4a98315f` changed only `ops/` documentation/state files and introduced no product-code or dependency change.

Conclusion: keep the current T003 pypdfium2/Pillow evidence adapter for the MVP route. This is a task-level reuse decision, not a durable architecture lock; re-open on the triggers recorded in the T005A report.

Next: T005B real-case generalization. Brief: `ops/T005B_REAL_CASE_GENERALIZATION.md`. Execution requires one genuinely new real academic case.


## 2026-10-01 — T005B input-gate reconnaissance (read-only)

Actor: Codex (local), on the user's instruction to sync `main`, take over the
sole NEXT, and first check whether local private data already holds an unused
real academic case usable for T005B.

Repository sync: `git fetch origin main` + `git merge --ff-only origin/main`
fast-forwarded `4a98315` → `29dde8a` (5 commits: T005A control-room review,
T005B activation, the `ops/T005B_REAL_CASE_GENERALIZATION.md` brief, and the
`AGENTS.md` gate update). No local work was lost.

Task: T005B's Human input gate requires one genuinely new real academic case to
be available to the local runtime, and allows Codex to identify such a case
already present in local private data without exposing private text to Git. This
step answered only that availability question.

Method (zero model/API calls; nothing written outside `ops/`): read-only
inventory of the project's private data directory, plus an inventory of the
machine-local academic PDF material that exists outside the repository, with
page-text extractability sampled through the project `.venv` pypdf.

Findings:

- the project's private data directory holds only the C04 case (used by
  T001-T004) and the synthetic probe fixtures, so **no unused real case exists in
  project private data**;
- genuinely unused real academic source material does exist on this machine
  outside the repository: text-native Chinese journal articles in political
  science / sociology, two large text-native book scans (one Chinese, one
  English), and one image-only facsimile whose sampled pages carry no text layer
  at all (a natural `needs_ocr` candidate);
- per T005B's privacy rule that material is deliberately **not named in Git**;
  it was identified to the user in-session only;
- a large machine-local periodical set is AES-encrypted and currently unreadable
  by the project's pypdf without adding a `cryptography` dependency, so it is not
  a first-choice T005B case.

Consequence: T005B's Human input gate is **not yet satisfied**. A candidate
primary-source PDF alone is not a case; the task still requires a real
secondary-source quotation/paraphrase the user actually wants to trace plus
whatever real clue is available (clues may be wrong). No product code,
dependency, retrieval configuration, or private source material was changed.

Gate: this is a read-only input-availability check. T005B execution has not
started and remains blocked on the user supplying or selecting one real case.


## 2026-10-01 — T005B real case executed: honest `needs_ocr` (0 model calls, $0.00)

Actor: Codex (local), on the user's explicit instruction to run the new real
case under `ops/T005B_REAL_CASE_GENERALIZATION.md` and to accept a real
`needs_ocr` result rather than adding OCR to force a success.

Model rule: live Codex runtime inspected before the work — provider `custom`
(DeepSeek), model `deepseek-flash`, reasoning `low`. No Goal/Ultra mode and no
multi-agent delegation, per D008.

Case (id `T005B-01`): a user-supplied secondary passage on Plato's treatment of
poetry in 《理想国》 Book X (clue: Stephanus 605B / 607B), traced against a
user-supplied 459-page local scan of 柏拉图《理想国》, 郭斌和、张竹明 译. The scan
was copied into `data/private/T005B-01/` and verified byte-identical by sha256
(`4d8d8c8a…739b`); the original file was untouched. The scanned colophon page
confirmed 商务印书馆, 1986, 郭斌和 张竹明 译 (that reading is source-observed;
author/title/translator came from the user, and retrieval inferred nothing).

New code: `tools/t005b_scan_probe.py` (zero-cost text-layer probe plus optional
page rendering for visual inspection) and `tools/t005b_case_run.py` (runs the
case through source scan -> retrieval ingest -> evidence object, stopping at the
first honest failure). No new dependency, no upstream modification, no
architecture change, no OCR.

Result: **`needs_ocr` at document level**, the failure state the brief asked
for. Stage 1: all 459 pages have no usable text layer (0 normalized characters
in the whole document; every sampled page is one full-page image and the pages
carry no font resources at all). Stage 2: PaperQA2 core-API `Docs.aadd` with the
pinned settings and an explicit citation fails closed —
`ValueError: This does not look like a text document` — indexing 0 documents and
0 chunks. Stage 3: localization was not attempted, because no candidate passage
exists and the case clue is a canonical reference rather than a PDF page label.
The paid query stage was deliberately not run and that decision is recorded in
the result object.

Honesty: no source text, page number, geometry or highlight was invented; the
secondary paraphrase is kept out of the source-evidence field
(`original_text = null`); the product reports a coverage/ingest limitation
instead of the false claim that the passage does not exist. T004's `needs_ocr`
status, previously proven only by a synthetic fixture, is now proven end to end
on real material.

Cost: **0 model calls, $0.00**. T003 probes re-run 15/15, T004 probes re-run
16/16 (both zero-cost). `C04.pdf` sha256 `d3e3b068…b48c1`, the T001 results JSON
sha256 `68238b48…c335` and the C04 PDF mtime are unchanged; C04 was not used as
evidence for this gate.

Gaps confirmed by this case: (1) there is no scan/OCR ingestion path — the
current stack cannot ingest an image-only source at all; (2) humanities
canonical clues (Book X, Stephanus 605B/607B) have no mapping to the pipeline's
PDF page-label hint; (3) the "a secondary paraphrase cannot be literally
matched" concern is recorded as an untested hypothesis, not a finding, because
this source has no text layer to test against.

Reuse-first: no new subsystem was written. `ops/REUSE_SCAN_2026-10-01.md`
already names the reusable OCR options (OCRmyPDF, PaddleOCR, MinerU, Docling,
with `citefact`'s Docling OCR path as precedent) and its guardrail forbids
building custom OCR before checking them; the T005B run therefore stopped at the
explicit OCR requirement.

Report: `ops/T005B_REAL_CASE_REPORT.md`. Gate: this is a coverage finding for
one real case. It authorizes no OCR work, no dependency install, and no
architecture change; adding an OCR engine or picking the next unit is a human
gate.


## 2026-10-01 — T005B control-room review passed

Actor: ChatGPT product control

Independent GitHub review accepted T005B as a PASS under its explicit pass condition. Commit `6b26998` used a genuinely new real case, produced document-level `needs_ocr` on a 459-page image-only scan, made 0 model/API calls, added no dependency/OCR engine, did not fabricate primary text/page/highlight evidence, and kept private source bytes under ignored private data. T003 regression remained 15/15 and T004 regression 16/16.

The two new scripts were reviewed as bounded test utilities: they scan the text layer, attempt the existing PaperQA2 ingest path, construct a T004-shaped honest failure object, and stop before OCR. No original private machine path is hard-coded; no core retrieval/evidence architecture is modified.

Conclusion: T005B is complete. The real case confirms scan/OCR ingestion as a product coverage gap and confirms that humanities canonical location clues are not yet mapped to PDF-page hints. The paraphrase-vs-literal-search concern remains untested and must not be promoted to a finding.

Next proposed unit: `ops/T006_OCR_REUSE_BENCHMARK.md`. Runtime installation remains behind a user human gate.


## 2026-10-01 — T006 Phase 1: static OCR reuse scan (no install, $0.00)

Actor: Codex (local), on the user's explicit instruction to run only T006
Phase 1 (the static Reuse Scan) and to install no OCR engine, model, or system
dependency.

Model rule: live Codex runtime inspected first — provider `custom` (DeepSeek),
model `deepseek-flash`, reasoning `low`. No Goal/Ultra mode and no multi-agent
delegation, per D008.

Sync note: `origin/main` had advanced five commits past the local checkout
(including the T006 brief and gate). Work was rebased onto `fadfb22` before
committing; the draft commit is preserved as `backup/t006-phase1-draft`.

Reuse gate walked in order: (1) repository capability — no OCR path, the T003
adapter requires a real text layer and fails closed; (2) native Codex
capability — the bundled `pdf` skill renders pages with Poppler but performs no
recognition; (3) available plugins — the only OCR-capable one is the hosted
Adobe Acrobat connector, which cannot be embedded in a self-hosted product;
(4) installable skills — none preferable; (5) maintained GitHub projects;
(6) official docs.

Local environment measured (zero cost): no `tesseract`, `gswin64c` or `magick`
on `PATH`; the project `.venv` already holds `torch` 2.14.1, `transformers`
5.18.0, `sentence-transformers` 6.1.0, `huggingface_hub` 1.33.0, `numpy`
2.4.6, `pypdfium2` 5.13.0, `Pillow` 12.3.0, `pypdf` 6.19.0, `litellm` 1.84.1
and `paper-qa` 2026.8.12.

Static verification via the GitHub connector (read-only, 2026-10-01): nine
candidates — OCRmyPDF (MPL-2.0, 34,913★, push 2026-09-29), RapidOCR
(Apache-2.0, 8,022★, 2026-10-01), Docling (MIT, 68,254★, 2026-10-01),
PaddleOCR (Apache-2.0, 90,490★, 2026-09-16), Surya (Apache-2.0, 21,434★,
2026-09-11), Marker (Apache-2.0, 40,146★, 2026-09-13), MinerU (Apache-2.0 plus
additional terms, 80,944★, 2026-09-30), DeepSeek-OCR (MIT, 23,925★, last push
2026-01-27, 289 open issues), Tesseract (Apache-2.0, 76,783★, 2026-09-28).

Two corrections to earlier notes were verified from the licence files rather
than assumed: MinerU `LICENSE.md` is "Apache License 2.0 ... subject to the
additional terms below" (separate commercial licence only above 100M MAU or
USD 20M monthly revenue, plus an online-service attribution obligation) — it is
not AGPL; and datalab-to/marker's `LICENSE` is the Apache License 2.0.

Result — the brief allows at most two runtime candidates, and exactly two were
approved in `ops/T006_OCR_REUSE_REPORT.md`: **OCRmyPDF** (only candidate whose
output feeds the proven PaperQA2 + T003 path unchanged, because it writes a
bounding-box-positioned text layer into the PDF; cost is Ghostscript + Tesseract
+ a `chi_sim` data pack) and **RapidOCR** (Apache-2.0, pure
pip/ONNXRuntime, no system binary, no torch; its README states the models are
PaddleOCR models converted to ONNX, so it takes the slot the brief reserved for
PaddleOCR). Not shortlisted, with reasons recorded: Docling (engine host that
would add a second document representation — the T005A objection to Ethos),
PaddleOCR (subsumed by its own ONNX conversion; kept as the named fallback),
MinerU (heavier than this step needs). Recorded as options: Surya/Marker,
DeepSeek-OCR, bare Tesseract. Not a route: the Adobe Acrobat plugin (hosted
SaaS).

Honesty / limits: nothing was executed, so Chinese character accuracy, reading
order and runtime on the 1986 商务印书馆 铅印 facsimile are unmeasured. The report
leaves its measured-results section and its ADOPT / PARTIAL_REUSE /
KEEP_NO_OCR_FOR_MVP recommendation explicitly PENDING Phase 2 instead of
guessing. Custom OCR code remains unjustified — at least five maintained
projects already do recognition, box geometry and page mapping.

Cost: **0 model calls, $0.00**; nothing installed, nothing downloaded, no
product code changed, no private source material read or modified.

Report: `ops/T006_OCR_REUSE_REPORT.md`. Gate: Phase 2 installs a dependency
and/or model weights, which this task did not authorize; selecting an OCR engine
stays a human decision.

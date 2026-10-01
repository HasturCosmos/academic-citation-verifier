# TASK_QUEUE

## DONE — T001

### M1-E1 PaperQA2 baseline preparation

Goal:
run one real gold-case baseline with the smallest possible setup and without prematurely modifying PaperQA2 core.

Before execution:
- C04 source PDF accessible to the coding/runtime environment: DONE;
- C04 gold-case definition accessible: DONE;
- live Codex model/provider/reasoning configuration inspected and verified: DONE;
- verify the current PaperQA2 setup path from upstream docs/repo: DONE — installed upstream-style as `pip install "paper-qa>=5"` into a project-local `.venv` (Python 3.11.9, `paper-qa` 2026.8.12); no source clone, no source modification;
- run-environment smoke test: DONE — `import paperqa` OK, `pqa --help` OK (exit 0), C04 PDF readable (1800 pages, page 109 text and gold phrase present);
- DeepSeek configurability, read-only: DONE — `deepseek/deepseek-chat` is a native LiteLLM provider keyed on `DEEPSEEK_API_KEY` and supports function calling;
- choose the lowest sufficient mode for the next execution step: DONE — chunking 1200/200 and the DeepSeek LLM roles pinned in the tracked `.pqa/settings/m1e1_c04.json`; embedding is the user-approved local SentenceTransformer (`sparse` was used only for the zero-API pre-check);
- corpus isolation and run mechanics: DONE — hardlinked corpus at `data/private/C04/pqa_corpus/C04.pdf` (gold case cannot be indexed), repo-local `PQA_HOME`, tracked settings file, sandbox egress limitation identified;
- zero-API parsing and recall pre-check: DONE — clean 1800-page pypdf parse, page-range chunk provenance, and the gold chunk ranked 4th by `retrieve_texts` with `sparse` (see PROJECT_STATE "M1-E1 parsing/retrieval evidence").

Remaining prerequisites for the first real baseline run:
- embedding choice RESOLVED and executed: the approved MiniLM was replaced after measurement showed its 128-token window truncates every 1200-char chunk; `st-BAAI/bge-small-zh-v1.5` (512 tokens, no truncation at 400-char chunks) is now pinned. `bge-m3` was downloaded and verified but rejected as CPU-impractical (~75+ min per embedding pass);
- first paid C04 baseline EXECUTED (one run, $0.01206): gold passage chunk at **rank 5**, labelled `pages 109-109`, raw 400-char chunk text, Top-5 met at the boundary, Top-1/Top-3 missed — detail in PROJECT_STATE "M1-E1 first baseline result";
- entry point adapted: the CLI agent is unusable for Chinese input (file-level `paper_search` tokenizer), so the run used PaperQA2's core API via `tools/m1e1_baseline_run.py`; no upstream source was modified.
- before the paid call, locally verify which current DeepSeek model name is accepted by the installed LiteLLM 1.84.1: DeepSeek's current official API uses `deepseek-flash`, while the earlier read-only inspection recorded `deepseek/deepseek-chat`;
- settings file that disables OpenAI-dependent defaults and narrows the paper directory: DONE (`.pqa/settings/m1e1_c04.json`, corpus isolated at `data/private/C04/pqa_corpus/`);
- writable PQA home and key injection path: DONE as a mechanism (`PQA_HOME=<repo>` → repo-local `.pqa/`; key comes from the session env or a git-ignored `.env`);
- user authorization for the baseline model spend: GRANTED on 2026-10-01 with no hard cap;
- baseline execution and spend recording: DONE.

Known risk to watch at run time:
- the agent's file-level `paper_search` layer uses a tantivy tokenizer that handles unmarked Chinese poorly; if the agent cannot locate any paper, retry with `agent.agent_type = "fake"` or a tightened tool set rather than changing retrieval code;
- escalation is required for the run itself because the sandbox has no network egress.
- this risk materialised: the agent path cannot retrieve the Chinese paper at all, which is why the executed run used the core API.

Baseline must record:
- whether gold enters Top-5;
- first-hit rank;
- whether raw text is available;
- PDF page provenance;
- surrounding context availability;
- code/config changes required;
- model/API cost.

Constraint:
first run should stay as close to upstream/default PaperQA2 behavior as practical.

## DONE — T002

Execution brief: `ops/T002_PLAN_BRIEF.md`

Plan artifact: `ops/T002_ARCHITECTURE_PLAN.md`

Status (2026-10-01): planning and short Reuse Scan completed. Plan reviewed and accepted as the basis for the next reversible experiment; this is not a durable final architecture decision.

- Recommended route: retain PaperQA2 retrieval with a separate pypdfium2/Pillow coordinate and screenshot evidence layer; Docling with preserved provenance is the first fallback.
- Confirmed experiment preference: highlight the whole candidate source passage, including cross-page passages.
- Proposed next experiment: reuse all 10 saved C04 candidates to test exact page/character coordinates and original-page highlighting with zero new model/API calls; see the plan for pass/fail criteria.
- Next experiment: NOT STARTED. Do not implement product code, install dependencies, or execute the experiment under this save-only authorization.
- Next gate: user review of the plan and explicit authorization to begin the experiment; durable architecture choices and milestone acceptance remain human decisions.

Decide how much of PaperQA2 to retain for M1 after:
1. the completed T001 evidence;
2. the newly confirmed PRODUCT_V0_1 requirements;
3. a short Reuse Scan of maintained alternatives/components.

Do not treat PaperQA2 as the whole product architecture merely because the baseline passed Top-5.

T001 evidence now available:
- it works, but only through an adapted entry point: gold at rank 5 (boundary Top-5), raw chunk text, exact page label, $0.012 per query, no upstream modification;
- chunk size is the strongest remaining lever (300-char chunks put the same gold chunk at rank 1 in the zero-cost pre-check);
- the built-in citation/metadata inference is useless for this Chinese book (docname `Rejoice2026`);
- the CLI agent's file search is Chinese-incompatible, so any product use needs an adapter or a different front end.

Possible outcomes:
- continue with a thin adapter;
- replace only a weak parsing/retrieval component;
- escalate to MinerU-based route.

## BLOCKERS

None at the local test-material / Codex-configuration layer.

Resolved on 2026-09-30:
- upstream PaperQA2 install/run path confirmed and exercised (`paper-qa` 2026.8.12 in project `.venv`);
- network access for dependency installation was authorized and used for that install;
- setup work was done at the project's medium reasoning effort, without multi-agent or Goal modes.

Execution prerequisites still pending:
- all of the above are now DONE: the local SentenceTransformer was installed and swapped in, the DeepSeek model-name check was run (live API offers only `deepseek-flash` and `deepseek-v4-pro`), and exactly one paid C04 baseline was executed with network escalation, recording rank, provenance, context and cost.

## BACKLOG

- M2 end-to-end MVP.
- M3 real-case evaluation set expansion.
- Additional C01-C05 regression cases.
- Strip repeated page furniture (running headers/footers) from candidate text and
  from highlight spans before the evidence is shown to a user (observed on T003
  page 130).
- PMS project (explicitly deferred).


## DONE — T003

Execution brief: `ops/T003_C04_HIGHLIGHT_EXPERIMENT.md`

Report: `ops/T003_C04_EVIDENCE_REPORT.md`

Goal:
validate the candidate-to-original-page-highlight evidence chain on the saved C04 candidates, reusing T001 retrieval artifacts and adding only the minimal pypdfium2/Pillow evidence layer.

Constraints:
- zero model/API calls;
- no rerun of T001 unless required by a missing artifact;
- no automatic Docling/MinerU/OCR fallback;
- no UI work;
- no durable architecture decision from this single case.

Status (2026-10-01): COMPLETE — PASS. All acceptance criteria met. User accepted T003 on 2026-10-01.

- dependencies added: `pypdfium2` 5.13.0, `Pillow` 12.3.0 (project `.venv`), nothing else installed;
- implementation: `tools/t003_evidence_localize.py` (thin evidence-localization adapter) and `tools/t003_regression_probes.py` (15 probes with synthetic non-private fixtures);
- 10/10 stored candidates `located` with a unique full match in the 1800-page PDF; gold candidate on PDF page 109; cross-page candidate split into page 130 + page 131 fragments;
- 11 evidence fragments, 140 highlight runs, 11 highlighted page images at 144 DPI, all visually inspected; every fragment passed the geometry sanity check (no clipped runs, render size equals device size, ink present in every highlight run);
- regression probes 15/15 (whitespace/line-wrap, repeated -> ambiguous, missing -> unmatched, cross-page, rotations 0/90/180/270, cropped page, no text layer -> needs_ocr, wrong hint -> whole-PDF fallback, gold whitespace rewrite);
- cost: 0 model/API calls, $0.00; `C04.pdf` and the T001 results JSON sha256-verified unchanged;
- known limitation carried forward: on a rotated page PDFium returns text in display order, so a passage spanning lines reordered by the rotation is reported `unmatched` (individual lines still localize and highlight correctly);
- next gate: user review of the report. This PASS is not a durable architecture decision and not M1 acceptance.



## DONE — T004

Execution brief: `ops/T004_END_TO_END_BACKEND_SLICE.md`

Report: `ops/T004_BACKEND_SLICE_REPORT.md`

Goal:
connect the real secondary-source query -> PaperQA2 core candidate retrieval -> T003 evidence localization/highlight -> structured evidence/citation output into the first backend vertical slice.

Constraints:
- reuse existing retrieval/evidence components;
- no full UI yet;
- no OCR/source-acquisition expansion;
- no invented bibliographic metadata;
- preserve multiple candidates;
- record actual model/API cost and regressions.

Status (2026-10-01): COMPLETE — PASS. All 12 acceptance criteria met; awaiting user review.

- entry point: `tools/t004_backend_slice.py`, run live from the real historical 38-character T001 query; PaperQA2 core API only (`Docs.aadd` + `Docs.aquery`), CLI agent never used;
- result: 10 candidates, 10/10 `located` with unique full matches, historical gold at retrieval **rank 2** resolving to **PDF page 109**, 11 highlighted page images, raw 400-character chunk text kept as copyable `original_text`;
- product object per candidate: `candidate_id`, `status`, `source_document_id`, `retrieval_rank`, `retrieval_score`, `original_text`, `pdf_page_numbers`, `printed_page_numbers` (empty), `highlighted_image_refs`, `original_page_image_refs`, `fragments` (geometry), `bibliographic_metadata`, `basic_footnote_citation`, `basic_reference_citation`, `warnings`, `unresolved_fields`;
- metadata honesty: citations use caller-supplied confirmed metadata only; the printed page is unresolved and no PDF page is substituted; PaperQA2's inferred docname is unused;
- cost: 11 model calls, 5722 prompt / 9308 completion tokens, **$0.0128862**; parse+embed+add 400.25 s, query 19.14 s, evidence 9.59 s;
- regression: T004 probes 16/16, T003 probes re-run 15/15, `C04.pdf` and the T001 results JSON sha256-verified unchanged;
- boundary: `ambiguous`/`unmatched`/`needs_ocr` are proven by probes only; no UI, no photo input, no source acquisition. This PASS is not durable architecture acceptance.

## NEXT CANDIDATE — T005 (proposed, not authorized)

Two options, in priority order:

1. **Real failure-state coverage**: run the same connected loop on at least one
   case that genuinely produces `ambiguous`, `unmatched` or `needs_ocr`, so the
   product's honest-failure states are proven on real material rather than only
   by probes (a scanned or mis-hinted page would do; no OCR build-out).
2. **Ranking stability**: measure the LLM evidence-reranking variance across
   repeated identical queries on the same index and decide whether the product
   should present retrieval-stage order, reranked order, or both. This is a
   product-behaviour question, not a ranking-optimisation task.

Also still in backlog: strip repeated page furniture from candidate text and
highlight spans before showing evidence to a user (seen again on `cand-09`,
pages 130–131).

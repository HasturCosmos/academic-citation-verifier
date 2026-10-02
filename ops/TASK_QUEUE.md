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

Status (2026-10-01): COMPLETE — PASS. All 12 acceptance criteria met. User accepted T004 on 2026-10-01.

- entry point: `tools/t004_backend_slice.py`, run live from the real historical 38-character T001 query; PaperQA2 core API only (`Docs.aadd` + `Docs.aquery`), CLI agent never used;
- result: 10 candidates, 10/10 `located` with unique full matches, historical gold at retrieval **rank 2** resolving to **PDF page 109**, 11 highlighted page images, raw 400-character chunk text kept as copyable `original_text`;
- product object per candidate: `candidate_id`, `status`, `source_document_id`, `retrieval_rank`, `retrieval_score`, `original_text`, `pdf_page_numbers`, `printed_page_numbers` (empty), `highlighted_image_refs`, `original_page_image_refs`, `fragments` (geometry), `bibliographic_metadata`, `basic_footnote_citation`, `basic_reference_citation`, `warnings`, `unresolved_fields`;
- metadata honesty: citations use caller-supplied confirmed metadata only; the printed page is unresolved and no PDF page is substituted; PaperQA2's inferred docname is unused;
- cost: 11 model calls, 5722 prompt / 9308 completion tokens, **$0.0128862**; parse+embed+add 400.25 s, query 19.14 s, evidence 9.59 s;
- regression: T004 probes 16/16, T003 probes re-run 15/15, `C04.pdf` and the T001 results JSON sha256-verified unchanged;
- boundary: `ambiguous`/`unmatched`/`needs_ocr` are proven by probes only; no UI, no photo input, no source acquisition. This PASS is not durable architecture acceptance.

## DONE — T005A evidence-layer reuse benchmark

Execution brief: `ops/T005A_ETHOS_REUSE_BENCHMARK.md`

Report: `ops/T005A_ETHOS_REUSE_REPORT.md`

Goal:
determine whether `docushell/ethos` should replace or shrink the custom T003
pypdfium2/Pillow evidence-localization layer before any more evidence-layer code
is written.

Constraints:
- reuse existing C04/T003/T004 artifacts;
- do not rerun PaperQA2 retrieval;
- zero model/API calls;
- no OCR implementation;
- no UI/source-acquisition work;
- no deletion of current T003 code during the benchmark;
- stop before installing a system-wide Rust/toolchain dependency solely for Ethos.

Status (2026-10-01): COMPLETE — **KEEP_CURRENT**. ChatGPT control-room review PASSED on 2026-10-01; no durable architecture lock is implied.

- Examined `docushell/ethos` Apache-2.0 at `main` `1101f0b6…` (2026-09-07, the
  v0.6.0 publication closeout), read-only via the GitHub connector.
- Phase 1 finding: no Windows-runnable path without installing a Rust 1.87.0
  toolchain. v0.6.0 ships macOS arm64 + Linux x64 CLI archives only; its own
  closeout states a Windows verify-only candidate was built and deliberately
  withheld because Windows packaged artifacts remain a blocked lane. The Python
  wheel is a thin wrapper around a caller-provided `ethos` CLI.
- Phase 2 was therefore **not run**: the T005A guardrail requires stopping before
  installing a system-wide toolchain solely for Ethos. This is a mandated stop,
  not an oversight.
- Capability finding: Ethos is a citation-verification/grounding layer over an
  already-parsed document, not a passage-localization layer. It matches our
  `needs_ocr` intent with `ocr_required`, but does not cover the fallible-hint
  search, the unique-match/ambiguity rule, cross-page fragment splitting, or
  per-line highlight runs.
- Consequence: zero T003/T004 code would be removed; adopting Ethos would add a
  toolchain, a subprocess, and a second document representation for the same
  behavior. Recorded as a future option with explicit re-open triggers.
- Cost: 0 model calls, $0.00; no dependency installed; no private source material
  modified.

## DONE — T005B real-case generalization

Execution brief: `ops/T005B_REAL_CASE_GENERALIZATION.md`

Report: `ops/T005B_REAL_CASE_REPORT.md`

Goal:
run the current product path on a genuinely new real academic case and record
either traceable evidence or an honest, reproducible failure status.

Status (2026-10-01): COMPLETE — real case passed through the current path and
**failed honestly with `needs_ocr`**. ChatGPT control-room review PASSED on 2026-10-01.

- Case `T005B-01`: a user-supplied secondary passage on Plato's treatment of
  poetry in 《理想国》 Book X (clue: Stephanus 605B / 607B) traced against a
  user-supplied 459-page local scan of 柏拉图《理想国》, 郭斌和、张竹明 译
  (商务印书馆 1986, confirmed from the scanned colophon page).
- Result: **`needs_ocr` at document level.** The scan is image-only — 459/459
  pages carry no usable text layer, 0 normalized characters in total, and every
  sampled page holds one full-page image with no font resources at all.
- The current retrieval component fails closed on it: PaperQA2 `Docs.aadd`
  raises `ValueError: This does not look like a text document` and indexes 0
  chunks. The paid query stage was deliberately not run; no candidate existed to
  retrieve.
- No evidence was fabricated: no source text, no highlight, no page number, and
  the secondary paraphrase is kept out of the source-evidence field.
- Cost: **0 model calls, $0.00**; no new dependency, no upstream change.
- Regression: T003 probes 15/15, T004 probes 16/16 (both zero-cost, unchanged);
  C04 hashes and mtime verified untouched.
- Gaps confirmed by real material (previously only synthetic): (1) no scan/OCR
  ingestion path — the stack cannot ingest an image-only source at all; (2)
  humanities canonical clues (Book X, Stephanus 605B/607B) have no mapping to
  this pipeline's PDF page-label hint.
- Boundary: this is a coverage finding for one real case. It is not an OCR
  authorization, not a durable architecture decision, and not M1 acceptance.

Also still in backlog: strip repeated page furniture from candidate text and
highlight spans before showing evidence to a user (seen again on `cand-09`,
pages 130–131).

## DONE — T006 Phase 1: static OCR reuse scan

Execution brief: `ops/T006_OCR_REUSE_BENCHMARK.md`

Report: `ops/T006_OCR_REUSE_REPORT.md`

Goal:
before installing anything, compare maintained OCR candidates and shortlist at
most two runtime candidates for the scan/OCR ingestion gap confirmed by T005B.

Status (2026-10-01): COMPLETE — static comparison delivered; Phase 2 awaits the
user's gate.

- Reuse gate walked in order: repository capability (no OCR path; the T003
  adapter needs a real text layer and fails closed) → native capability (the
  bundled `pdf` skill renders with Poppler but performs no recognition) →
  available plugins (only the hosted Adobe Acrobat connector, not embeddable) →
  installable skills (none preferable) → maintained GitHub projects →
  official docs.
- Nine candidates verified read-only through the GitHub connector on
  2026-10-01 (license, stars, last push, Chinese support, Windows install,
  page provenance, added infrastructure). Local facts measured: no `tesseract`,
  `gswin64c` or `magick` on `PATH`; `torch` 2.14.1 and `pypdfium2` 5.13.0
  already in the `.venv`.
- **Approved runtime candidates (the brief's maximum of two):** OCRmyPDF
  (`--language chi_sim`) — only candidate whose output feeds the proven
  PaperQA2 + T003 path unchanged, because it writes a bounding-box-positioned
  text layer into the PDF; and RapidOCR (`pip install rapidocr onnxruntime`) —
  Apache-2.0, CPU-only ONNXRuntime, no system binary, no torch, and its own
  README states the models are PaddleOCR models converted to ONNX.
- Explicitly not shortlisted: Docling (engine *host*, adds a second document
  representation), PaddleOCR (subsumed by its own ONNX conversion, kept as the
  named fallback if RapidOCR accuracy is insufficient), MinerU (heavier than
  this step needs). Recorded as options: Surya/Marker, DeepSeek-OCR, bare
  Tesseract.
- Corrections to earlier notes, verified from license files: MinerU is
  Apache-2.0 with additional commercial thresholds (100M MAU / USD 20M monthly
  revenue) and an online-service attribution obligation — not AGPL; Marker is
  Apache-2.0.
- Gap left open on purpose: nothing was executed, so Chinese character accuracy,
  reading order and runtime on the 1986 商务印书馆 铅印 facsimile are unmeasured.
  The report marks the measured-results and ADOPT/PARTIAL_REUSE/KEEP_NO_OCR
  sections as PENDING Phase 2 rather than guessing them.
- Cost: 0 model calls, $0.00; nothing installed or downloaded; no product code
  changed; no private source material read or modified.

## DONE — T006 Phase 2: bounded OCR runtime benchmark + experimental OCR path

Execution brief: `ops/T006_OCR_REUSE_BENCHMARK.md`
Batch brief: `ops/OVERNIGHT_GOAL_2026-10-01.md`
Report: `ops/T006_OCR_REUSE_REPORT.md`
Demo: `ops/T006_DEMO.md`

Status (2026-10-02): COMPLETE — executed under the user-authorized overnight
batch. Recommendation recorded: **PARTIAL_REUSE** (RapidOCR as an optional,
explicitly triggered scan-ingestion component; default text-layer path
unchanged). Durable adoption remains a Human Gate and was NOT taken.

- Sample frozen before any engine ran: PDF pages 1, 3, 10, 30, 200, 420 at
  300 dpi, hashes in `data/private/T006-01/sample_manifest.json`.
- **OCRmyPDF: `BLOCKED_INSTALL`.** The pip package installs, but the runtime
  fails with `EXIT=3` — no Ghostscript (`HKLM\SOFTWARE\Artifex\GPL Ghostscript`)
  and no Tesseract (`HKLM\SOFTWARE\Tesseract-OCR`), and the only package manager
  present is machine-wide/elevation-only Chocolatey. Recorded, not pursued.
- **RapidOCR: works.** 3.9.2 + onnxruntime 1.30.0; the three PP-OCRv6 ONNX models
  ship inside the wheel (no download). Frozen sample: 99 body lines, mean line
  confidence 0.996–0.998 on body pages, ≈9.5 s/page at 300 dpi.
- Accuracy honesty: no certified ground truth exists, so **no CER number is
  claimed**. A bounded agent visual cross-check over the 99 body lines found 1
  genuine character substitution (stylised title type), 1 punctuation
  substitution, a few punctuation-width differences, 2 bracket variants, 3
  margin tokens merged into body lines, and 1 dropped character in a spaced
  running head.
- Full-document run: **459/459 pages**, 0 pages without text, 239,966 characters,
  59.3 min wall clock, 399.4 MB git-ignored cache.
- Integration: upstream `paperqa.readers.chunk_pdf` (400/100) +
  `Docs.aadd_texts`/`retrieve_texts` with the pinned local embedding + the
  unchanged `t004_backend_slice.build_evidence_object`, with only three
  overridden methods in one new `PdfEvidenceSource` subclass. No existing
  component changed, no existing dependency upgraded.
- Real-case re-run (T005B-01): `needs_ocr` → 10 `located` evidence objects with
  verified highlight geometry, 0 model calls, $0.00. The cited region (Book X
  poetry expulsion) is **rank 7** → PDF pages 417–418, carrying the verified
  Stephanus `607` margin marker; **Top-1 miss, Top-10 hit**.
- Bonus bounded measurement: the margin carries the Stephanus series
  (75 three-digit margin numbers, observed range 328–663, plus 444 A–E section
  letters). Case clue `605` → PDF page 415 and `607` → PDF page 418, both
  verified against the page images. This is the first concrete route found for
  T005B's canonical-clue gap.
- Regression: T003 **15/15**, T004 **16/16**, new T006 probes **5/5**;
  `C04.pdf` sha256 `d3e3b068…b48c1` and the T001 results JSON sha256
  `68238b48…c335` re-verified unchanged, C04 mtime untouched.
- Cost: **0 model calls, $0.00** for the whole task. No paid/API OCR, no
  administrator action, no WSL/Docker/CUDA, no system-wide change.

## DONE — Authorized long-run MVP productization (MVP candidate delivered)

Execution brief: `ops/MVP_PRODUCTIZATION_GOAL_2026-10-02.md`

Report: `ops/MVP_CANDIDATE_REPORT_2026-10-02.md`

Status (2026-10-02): COMPLETE — **MVP candidate delivered and verified**.
Codex does not self-accept **MVP COMPLETE**.

- Stage 0 reuse scan: stdlib `http.server` local app chosen over Streamlit/Gradio/
  React because it adds no dependency, no build step and no deployment surface.
- Stage 1 reproducibility: `requirements.txt` (pinned, core vs optional OCR) and
  `requirements.freeze.txt` (118-package export); CPython 3.11.9; `pip check`
  clean; all 9 pins match. A from-scratch network install was not executed.
- Stage 2 entry point: `tools/mvp_app.py` (loopback web app + `--run-once`) over
  `tools/mvp_pipeline.py`; text-layer default, RapidOCR optional fallback,
  honest `insufficient_source` when neither exists; staged input confirm with a
  simple multi-item splitter and manual edit.
- Stage 3 result experience: four-way product state, progressive disclosure,
  copyable text, highlighted original page, PDF page with printed page left
  unresolved, metadata-honest citations, OCR warning, no accuracy percentage.
- Stage 4 routes: Route A C04 text-layer (10/10 located, gold **PDF page 109 rank 3**)
  and Route B T005B-01 scan (15/15 located, Stephanus `607` → **PDF pages 417–418
  rank 7**) both through the entry point at **0 model calls / $0.00**; one real
  honest failure (`--ocr-mode off` on the 459-page image-only scan) →
  `insufficient_source` with 0 candidates.
- Stage 5 cleanup: display-only margin-noise rule (evidence text and highlight
  geometry untouched, hidden tokens reported); experimental wording removed from
  the product surface; relative image paths fixed and served through a guarded
  endpoint; README rewritten.
- Stage 6 tests: `tools/mvp_probes.py` **44/44** (zero-cost, synthetic PDF
  fixtures), T003 **15/15**, T004 **16/16**, T006 **5/5**, live web smoke passed.
- Integrity: `C04.pdf` `d3e3b068…b48c1`, T001 results JSON `68238b48…c335`,
  T005B-01 scan `4d8d8c8a…739b` re-verified unchanged; `git ls-files data/private`
  empty.
- Boundary: acceptance bar met except the unexecuted from-scratch install; the
  result is a candidate, not an accepted MVP.

## DONE — MVP milestone accepted

Status (2026-10-02): **MVP COMPLETE** after ChatGPT control-room PASS + explicit user acceptance (D019).

Deferred to post-MVP backlog by user decision:
- paid LLM rerank;
- certified human OCR-accuracy verification;
- printed-page mapping;
- same-query multi-edition / multi-translation comparison.

Do not reopen these as MVP blockers.

## DONE — POST-MVP PATCH: PRIMARY-SOURCE INTAKE

Real pilot finding: `ops/PILOT_FINDING_2026-10-02_PRIMARY_SOURCE_INTAKE.md`

Execution brief: `ops/POST_MVP_PRIMARY_SOURCE_PATCH_GOAL_2026-10-02.md`

Report: `ops/POST_MVP_PRIMARY_SOURCE_PATCH_REPORT_2026-10-02.md`

Status (2026-10-02): COMPLETE. Not a new MVP milestone; does not reopen D019.

- P0 fixed: blank/whitespace metadata means "no metadata"; metadata is read only when
  it exists and is a regular file; directory/missing/invalid input gives a Chinese
  message instead of `PermissionError [Errno 13]` or a traceback; `run_job` also
  catches `SystemExit` so a validation failure cannot leave a job stuck.
- P1 delivered: primary-source **PDF upload** is the normal web path; uploads stay
  under the git-ignored `data/private/mvp_uploads/`; a forged upload path is refused;
  C04/T005B-01 remain as labelled built-in demo/cached examples; manual local path +
  metadata JSON is an advanced fallback.
- Format policy before the job starts: PDF only; EPUB rejected with the pagination /
  original-page-image explanation; no fabricated page numbers.
- Tests: `mvp_probes` **70/70** (44 before the patch), T003 **15/15**, T004 **16/16**,
  T006 **5/5**; 0 model calls, $0.00.
- The original pilot input now completes over the real HTTP surface (job done,
  `multiple_candidates`, no `PermissionError`).

## NEXT — RESUME POST-MVP PILOT USE

Control-room review: **PASS** for the primary-source intake patch.

- Run the accepted MVP + this patch on the user's real literature-tracing tasks.
- Record concrete value and failure evidence (what it found, what it missed, why).
- Fix only defects that materially block real use; keep patches small and reversible.
- Then package the concise internship/demo story.

Separate future Human Gate (unchanged): lawful/open/authorized source acquisition when
the user lacks a PDF. Do not integrate unauthorized/pirated repositories.


## DONE — AUTHORIZED OVERNIGHT GOAL: LAWFUL SOURCE ACQUISITION PHASE 1

Execution brief: `ops/SOURCE_ACQUISITION_OVERNIGHT_GOAL_2026-10-02.md`
Report: `ops/SOURCE_ACQUISITION_PHASE1_REPORT_2026-10-03.md`
Reuse scan: `ops/SOURCE_ACQUISITION_REUSE_SCAN_2026-10-03.md`

Status (2026-10-02): COMPLETE. Experimental and reversible; not a durable
architecture decision and not a new MVP milestone (D019 stays closed).

- Reuse First executed live: OpenAlex and Internet Archive adopted (real open
  PDFs), Google Books adapted but blocked by the anonymous daily quota (HTTP
  429), OAPEN/DOAB DEFER (DSpace REST 403 for this address), Unpaywall rejected
  (superseded by OpenAlex), 中文维基文库 adopted as a lead only.
- New `tools/source_acquisition.py`: one normalized schema, six keyless adapters,
  a term-overlap relevance guard, and download guardrails (evidence-eligible
  only, http(s) only, `%PDF` header, size cap, git-ignored target, provenance
  JSON with sha256).
- Reversible product route: `③b 查找开放全文` → `/find` → `/use_found` in
  `tools/mvp_app.py`. Uploaded/registered primary PDFs remain the primary path
  and are unchanged.
- Two lawful open PDFs actually downloaded and verified (IA public-domain scan
  524 pages / 33.5 MB; ANU Press OA book 312 pages), and the acquired PDF ran
  through the **unchanged** pipeline (text_layer, 2466 chunks, 5 candidates,
  4 located, 6 highlight images). Honest `USER_UPLOAD_REQUIRED` for the
  in-copyright Chinese translation case.
- Tests (0 model calls, $0.00): `mvp_probes` **70/70**, T003 **15/15**, T004
  **16/16**, T006 **5/5**, new source-acquisition probes **83/83**.
- No new dependency; one small pipeline hardening (metadata-as-dict callers no
  longer need to know about `ocr_cache`/`citation`/`notes`).

## NEXT — HUMAN GATE (source acquisition Phase 1)

Three decisions belong to the user, and no further engineering should start
before them:

1. create a free Google Books API key (a credential → gated) or accept that the
   anonymous quota makes Google Books unusable;
2. confirm whether OAPEN/DOAB answer from the user's own network (the adapter is
   already written) or accept that the OA-book route stays closed here;
3. confirm whether the experimental finder is kept, adjusted or dropped.

Durable OCR/source-acquisition adoption, paid services, credentials,
login/borrowing automation and any architecture expansion beyond the thin
optional finder remain Human Gates. The primary-PDF upload path stays primary.

## NEXT — RESUME POST-MVP PILOT USE (unchanged)

Run the accepted MVP (+ the intake patch + the optional finder) on real
literature-tracing tasks, record value/failure evidence, and package the
internship/demo story once the Human Gate above is settled.

## NEXT — POST-MVP PILOT WITH EXPERIMENTAL FINDER

Control-room review: **PASS** for source-acquisition Phase 1 as experimental/reversible.

Do not create credentials or expand providers yet. First:
- tighten two low-risk eligibility guardrails (IA explicit rights/license signal; OpenAlex per-location OA/access signal);
- then use the finder on real user literature-tracing tasks;
- keep primary PDF upload as the reliable default;
- promote Google Books API key / OAPEN-DOAB troubleshooting only if real pilot evidence shows the current finder is materially insufficient.

The finder is not yet a durable architecture commitment.

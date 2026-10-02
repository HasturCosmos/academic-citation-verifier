# PROJECT_STATE

Last updated: 2026-10-02 (MVP COMPLETE + intake patch + source-acquisition Phase 1 complete)

## Project

二流文科生的二手文献引用助手.

## Current phase

Gate 0 product definition: CLOSED.
Current technical stage: **MVP COMPLETE** (accepted 2026-10-02, D019) with the **post-MVP primary-source intake patch applied** (2026-10-02, report `ops/POST_MVP_PRIMARY_SOURCE_PATCH_REPORT_2026-10-02.md`). The authorized productization Goal `ops/MVP_PRODUCTIZATION_GOAL_2026-10-02.md` was executed; candidate report `ops/MVP_CANDIDATE_REPORT_2026-10-02.md`. T006 Phase 2 is complete and reviewed. T004 end-to-end backend vertical slice COMPLETE and PASSED (12/12); the proven retrieval and evidence layers produce ranked candidates with page-accurate highlighted Chinese original text and metadata-honest citation shells. The product entry point is `tools/mvp_app.py` over `tools/mvp_pipeline.py`. T005A returned KEEP_CURRENT; T005B ran the first genuinely new real case (T005B-01) and **failed honestly with `needs_ocr`** on an image-only 459-page scan, confirming two real gaps: no scan/OCR ingestion path, and no mapping from humanities canonical clues to the pipeline's PDF-page hint. T006 Phase 2 is executed: the benchmark is complete, an OCR path has been validated on the real scan, and a one-command demo exists. Recommendation recorded: **PARTIAL_REUSE** of RapidOCR as an optional, explicitly triggered scan-ingestion component. The `needs_ocr` coverage gap is closed for this source (459/459 pages OCR'd, 0 model calls, $0.00); the canonical-clue gap now has a verified route (Stephanus margin markers recovered by OCR).

T006 Phase 1 (static OCR reuse scan) COMPLETE on 2026-10-01 — report `ops/T006_OCR_REUSE_REPORT.md`. Nine candidates were verified read-only through the GitHub connector (license, activity, Windows story, Chinese support, geometry output, added weight) and reduced to the two shortlisted runtime candidates the brief allows: **OCRmyPDF** (writes a bounding-box-positioned text layer into the PDF, so the existing PaperQA2 + T003 evidence path is reused unchanged; cost is Ghostscript + Tesseract + a `chi_sim` data pack) and **RapidOCR** (Apache-2.0, pure pip/ONNXRuntime, no system binary, PaddleOCR models converted to ONNX, needs a thin boxes→evidence-fragment adapter). Docling was excluded as an engine *host* that would add a second document representation, PaddleOCR as subsumed by its own ONNX conversion, and MinerU as heavier than this step needs. Two earlier notes were corrected from license files: MinerU is Apache-2.0 with additional commercial thresholds (not AGPL), and Marker is Apache-2.0. **Nothing was installed or downloaded**, so Chinese accuracy on the facsimile is still unmeasured; Phase 2 is the human gate.

## Current status

- **Source-acquisition Phase 1 control-room review PASSED on 2026-10-03** as an experimental, reversible capability.
- Proven: lawful/open PDF acquisition can succeed and feed the unchanged evidence pipeline; closed/in-copyright Chinese translation case correctly falls back to USER_UPLOAD_REQUIRED.
- Before durable adoption, tighten open-access eligibility rules for Internet Archive collection-only signals and OpenAlex per-location OA/access signals.

- **Lawful source-acquisition Phase 1 COMPLETE (2026-10-02).** Report: `ops/SOURCE_ACQUISITION_PHASE1_REPORT_2026-10-03.md`; reuse scan: `ops/SOURCE_ACQUISITION_REUSE_SCAN_2026-10-03.md`. Experimental and reversible; not a durable architecture decision and not a new MVP milestone (D019 stays closed).
- New `tools/source_acquisition.py` (stdlib only, no new dependency): one normalized record schema, six keyless lawful adapters (OpenAlex, Internet Archive, Google Books, OAPEN, DOAB, 中文维基文库), a term-overlap relevance guard (`match_score`, floor 0.5) that stops an unrelated open PDF from being announced, and download guardrails — evidence-eligible records only, http(s) only, `%PDF` header check, size cap, writes only under git-ignored `data/private/`, and a `.provenance.json` with provider/landing/PDF URL/licence/bytes/sha256.
- Product route (reversible): `③b 查找开放全文` → `/find` → `/use_found` → download → the **existing** confirm/run flow in `tools/mvp_app.py`. The uploaded/registered primary-PDF path is unchanged and remains the primary route.
- Real evidence: two lawful open PDFs actually downloaded and validated — Internet Archive public-domain scan (*Plato's Republic: the Greek text*, 524 pages, 33,487,839 bytes, sha256 `e2d45f73…`) and an OpenAlex/ANU Press OA book (312 pages, 1,275,990 bytes, sha256 `4df2c549…`). The acquired PDF then ran through the **unchanged** canonical pipeline: `text_layer`, 2466 chunks, 5 candidates, 4 located, 6 highlighted original pages, 0 model calls, $0.00. The in-copyright Chinese case (理想国 郭斌和 张竹明) honestly returns `USER_UPLOAD_REQUIRED`; Internet Archive lending (`inlibrary`/`printdisabled`) and `private`/`access-restricted-item` files are refused in code with recorded reasons.
- Provider findings: Google Books 429s on the anonymous daily quota on every call (adapter supports an optional `GOOGLE_BOOKS_API_KEY`; **no key was created** — credential → Human Gate); OAPEN/DOAB DSpace REST answers this machine with 403 `You address is not allowed to access this API` (OAI-PMH answers but has no free-text search) → DEFER; Unpaywall rejected as superseded by OpenAlex; 中文维基文库 adopted as a lead only, never evidence. OpenAlex `pdf_url` values are claims: three of three eligible candidates for one query were refused by the header guard (Brill HTML, OpenEdition 502, Durham 403).
- Verification (0 model calls, $0.00): `mvp_probes` **70/70**, T003 **15/15**, T004 **16/16**, T006 **5/5**, new `source_acquisition_probes` **83/83**. `git ls-files data/private` empty; downloaded PDFs stay in git-ignored `data/private/sa_benchmark/`.
- One small hardening: `tools/mvp_pipeline.py` now fills `ocr_cache`/`citation`/`notes` when a caller supplies `metadata` as a dict, so that documented path no longer raises `KeyError: 'ocr_cache'`.
- NEXT is a **Human Gate**, not more engineering: (1) free Google Books API key or accept the quota block; (2) confirm whether OAPEN/DOAB answer from the user's own network (adapter already written) or accept the OA-book route as closed here; (3) confirm whether the experimental finder is kept.
- Unauthorized/pirated acquisition remains prohibited and out of scope.


- **Primary-source intake patch control-room review PASSED on 2026-10-02.** Independent review confirmed the blank-metadata fix, first-class primary PDF upload, early EPUB/non-PDF rejection, upload-path guard, and preserved registered demo routes.
- The MVP milestone remains accepted and closed; this patch is now part of the post-MVP working baseline.


- **Post-MVP primary-source intake patch COMPLETE (2026-10-02).** Report: `ops/POST_MVP_PRIMARY_SOURCE_PATCH_REPORT_2026-10-02.md`.
- P0 fixed: blank/whitespace metadata now means "no metadata"; a metadata path is read only when it exists and is a regular file; directory, missing, unreadable and invalid-JSON metadata produce a Chinese message instead of `PermissionError [Errno 13]` or a traceback.
- P1 delivered: **uploading a primary-source PDF is the normal web path**; uploads are written only under the git-ignored `data/private/mvp_uploads/`, a forged upload path is rejected, C04/T005B-01 remain as labelled built-in demo/cached examples, and the manual local path + metadata JSON moved into an advanced fallback.
- Format policy enforced before a job starts: PDF only (text layer or RapidOCR scan); EPUB is rejected with the reason (no fixed pagination, no locatable original page image) and no fake page numbers are invented.
- Verification: `tools/mvp_probes.py` **70/70** (44 before the patch), T003 **15/15**, T004 **16/16**, T006 **5/5**; 0 model calls, $0.00. The original pilot input (blank metadata + custom local PDF path) now completes over the real HTTP surface with no traceback.
- Next: resume real pilot use on the user's own literature tasks, record value/failure evidence, fix only defects that block real use, then package the internship/demo story.
- Separate future Human Gate (unchanged): lawful/open/authorized source acquisition when the user has no PDF.


- **MVP milestone formally accepted by the user on 2026-10-02 (D019).**
- The current build is now the accepted MVP baseline. Do not reopen paid LLM rerank, certified OCR accuracy, printed-page mapping or same-query multi-edition comparison as MVP blockers; they are post-MVP backlog.
- Next phase is **post-MVP pilot + portfolio/demo packaging**: use the accepted MVP on the user's real literature work, collect concrete failure/benefit evidence, and package a concise demonstrable story for internship use before expanding architecture.


- **MVP candidate control-room review PASSED on 2026-10-02.** ChatGPT product control recommends accepting the MVP milestone; final milestone acceptance remains the user Human Gate.
- Review correction: fresh-environment install is documented but unverified; same-query multi-edition comparison is not implemented (one primary source per run) and remains backlog. These are not treated as hidden completed features.


- **MVP candidate delivered on 2026-10-02** (authorized batch `ops/MVP_PRODUCTIZATION_GOAL_2026-10-02.md`). Report: `ops/MVP_CANDIDATE_REPORT_2026-10-02.md`. Canonical launch command: `$env:PQA_HOME=$PWD; .\.venv\Scripts\python.exe tools\mvp_app.py` → <http://127.0.0.1:8765>.
- One canonical entry point (`tools/mvp_app.py`: loopback-only stdlib web app + `--run-once`) over one shared contract (`tools/mvp_pipeline.py`): text-layer PDFs take the accepted T003/T004 evidence path; image-only scans take the adopted RapidOCR fallback; a source with neither returns an honest `insufficient_source` result that is still written and viewable.
- Both real routes ran through that entry point at **0 model calls / $0.00**: Route A (C04 text-layer, 5844 chunks, 10 candidates, **10/10 located**, gold on **PDF page 109 at rank 3**, 11 highlight images, cross-page candidate on 130–131); Route B (T005B-01 scan, 459 OCR pages, 846 chunks, 15 candidates, **15/15 located**, Stephanus `607` region on **PDF pages 417–418 at rank 7**, 27 highlight images).
- One real honest failure through the same entry point: T005B-01 (459 pages, 0 usable text-layer pages) with `--ocr-mode off` → `insufficient_source`, 0 candidates, blocker `ocr_disabled_by_request`; an existing OCR cache is never used silently when OCR is turned off.
- Product surface: staged input (pasted text / secondary PDF / photo) → confirm-or-edit text (simple multi-item splitter, no invented detection subsystem) → four-way result state (`evidence_found` / `multiple_candidates` / `no_corresponding_passage` / `insufficient_source`) → per-candidate copyable original text, highlighted original page, PDF page, known metadata, copyable footnote + reference citations, unresolved fields and warnings.
- Reproducibility: `requirements.txt` (pinned, layered core vs optional OCR) + `requirements.freeze.txt` (exact 118-package export of the verified machine); `pip check` clean and all 9 pins match the installed environment; CPython 3.11.9. A from-scratch network install was **not** executed and is the one unverified acceptance item.
- Verification: `tools/mvp_probes.py` **44/44** (zero-cost, synthetic-PDF end-to-end fixtures, no private material), T003 **15/15**, T004 **16/16**, T006 **5/5**, live web smoke (`GET /` 200, `POST /extract` 200, out-of-run `/asset` 403).
- Integrity re-verified after all runs: `C04.pdf` sha256 `d3e3b068…b48c1`, T001 results JSON `68238b48…c335`, T005B-01 scan `4d8d8c8a…739b`; `git ls-files data/private` empty.
- New tooling (all reversible, committed): `tools/mvp_app.py`, `tools/mvp_pipeline.py`, `tools/mvp_probes.py`, `tools/mvp_sources.json`. No existing product code was deleted or replaced and no default path changed.
- Boundary at delivery time: this was an **MVP candidate**, not MVP acceptance. The user accepted the milestone on 2026-10-02 (D019), so this row is history, not current status.

- **D018 confirmed on 2026-10-02:** until a direct ChatGPT↔Codex control connector exists, default to one-shot long Codex Goals for coherent reversible work; GitHub carries checkpoints/results; the user should only start Codex once and return for a genuine Human Gate or final acceptance.


- **D017 confirmed on 2026-10-02:** RapidOCR is adopted as the MVP's optional scan-ingestion fallback; the text-native route remains default; OCRmyPDF remains backlog.
- Active long-run execution brief: `ops/MVP_PRODUCTIZATION_GOAL_2026-10-02.md`.
- Productization target: reproducible environment + canonical product entry point + shared text-native/scan result contract + minimal user-facing surface + two real end-to-end routes + honest failure path + MVP candidate acceptance report.


- Overnight Goal control-room review PASSED on 2026-10-02 at **Level 3**: bounded OCR benchmark complete, experimental RapidOCR integration validated on the real T005B-01 scan, and a one-command experimental HTML demo exists. This is **not MVP acceptance**.
- Independent review confirmed the OCR adapter reuses T003/T004 rather than forking the evidence path; the demo uses real private scan/OCR/retrieval/highlight artifacts rather than mock data; the final image-path defect was fixed in commit `4ede43d`.
- Productization gap identified at control-room review: the repository still has no committed dependency manifest/lockfile (`requirements.txt`, `pyproject.toml`, etc.), so clone-to-run reproducibility is a required item in the active MVP productization Goal.


- New clean Project created in ChatGPT.
- Project Instructions v1.1 installed.
- Migration baseline created and accepted.
- Research First completed.
- GitHub connector confirmed working.
- This repository is the shared state bus for Chat / Work / Codex.
- Confirmed product definition: `ops/PRODUCT_V0_1.md`.
- Final product name confirmed on 2026-10-01: **二流文科生的二手文献引用助手**.
- T002 architecture plan reviewed: keep PaperQA2 as the retrieval component for the next experiment and test a separate pypdfium2/Pillow evidence-localization layer. This is an experimental route, not a durable final architecture decision.
- T003 executed the saved-candidate -> page geometry -> original-page highlight experiment on the 10 stored C04 candidates: 10/10 located, gold on PDF page 109, cross-page candidate split across pages 130/131, 15/15 regression probes passed, 0 model/API calls. User accepted T003 on 2026-10-01. Full report: `ops/T003_C04_EVIDENCE_REPORT.md`.
- T004 executed the end-to-end backend vertical slice: real historical T001 query -> PaperQA2 core retrieval (10 candidates, agent not used) -> T003 localization (10/10 located, historical gold at retrieval rank 2 on PDF page 109, 11 highlighted page images) -> product evidence objects with copyable original text, explicit statuses, unresolved-field reporting and Chinese citation shells. Cost $0.0128862 (11 model calls, 5722/9308 tokens); 12/12 acceptance criteria passed. Report: `ops/T004_BACKEND_SLICE_REPORT.md`.
- A backend vertical slice now exists end to end; there is still no product UI, no image/photo input path, and no external source acquisition.
- T004 determinism observation: T001 and T004 retrieved the same 10 chunk pages but the LLM evidence reranking reordered them (gold rank 5 vs rank 2; embedding-only diagnostic rank 3), so rank is not yet a stable product signal.
- M1-E1 PaperQA2 baseline is COMPLETE. PaperQA2 is installed as a package in the project `.venv`; no upstream source was cloned or modified.
- One paid DeepSeek-backed baseline was executed: gold passage rank 5 / Top-5 met, exact PDF page label preserved, raw chunk surfaced, cost $0.01206.
- T006 Phase 2 is COMPLETE (2026-10-02). Report: `ops/T006_OCR_REUSE_REPORT.md`; demo instructions: `ops/T006_DEMO.md`. The authorized batch brief was `ops/OVERNIGHT_GOAL_2026-10-01.md`. Project-local benchmark dependencies were installed; paid/API OCR, elevation and system-wide changes were never used.
- New experimental tooling (all reversible, committed): `tools/t006_ocr_benchmark.py` (freeze the sample, run a shortlisted engine), `tools/t006_ocr_evidence.py` (resumable per-page OCR cache + the OCR-backed `PdfEvidenceSource`), `tools/t006_ocr_pipeline.py` (OCR → upstream chunker → local-embedding retrieval → the unchanged T004 evidence builder), `tools/t006_ocr_probes.py` (5 zero-cost probes), `tools/t006_margin_scan.py` (margin/Stephanus measurement), `tools/t006_demo.py` (one-command two-stage demo). No existing product code was deleted or replaced and no default path changed.
- Benchmark outcome: **OCRmyPDF = `BLOCKED_INSTALL`** (Ghostscript + Tesseract absent; only an elevation-requiring Chocolatey route exists). **RapidOCR = works** — 3.9.2 + onnxruntime 1.30.0, ONNX models shipped in the wheel, ≈9.5 s/page at 300 dpi on CPU. Frozen sample (PDF pages 1, 3, 10, 30, 200, 420) produced 99 body lines with mean line confidence 0.996–0.998.
- Honesty boundary on accuracy: **no certified ground truth exists, so no CER/accuracy number is claimed.** A bounded agent visual cross-check found one genuine character substitution (stylised display type), one punctuation substitution, a few punctuation-width differences, two bracket variants, three margin tokens merged into body lines and one dropped character in a spaced running head. A certified human transcription and a second real scan case remain owed before any accuracy claim is published.
- Full-document OCR: **459/459 pages, 0 pages without text, 239,966 characters, 59.3 min wall clock, 399.4 MB git-ignored cache** (PNGs dominate; a production version would not persist them).
- Real-case result: T005B-01 went from `needs_ocr` to **10/10 `located`** evidence objects with verified highlight geometry, 0 model calls, $0.00. The cited region (Book X, expelling poetry) is **rank 7 → PDF pages 417–418**, the page whose right margin carries the verified Stephanus `607` marker; **Top-1 miss, Top-10 hit**. Retrieval was embedding-only and deliberately not LLM-reranked (that would have needed a paid call), so this reproduces T001/T004's mid-list ranking behaviour.
- Canonical-clue route (bounded measurement, not a shipped feature): the facsimile's margins carry the Stephanus series — 75 three-digit margin numbers (observed range **328–663**) and 444 A–E section letters. Case clue `605` → PDF page **415** and `607` → PDF page **418**, both verified against the page images. This is the first concrete route found for T005B's canonical-clue gap; the mapping is geometry-inferred and must stay human-verifyable.
- Regression after the experiment: T003 **15/15**, T004 **16/16**, new T006 probes **5/5**; `C04.pdf` sha256 `d3e3b068…b48c1` and the T001 results JSON sha256 `68238b48…c335` re-verified unchanged, C04 mtime untouched. Whole task cost: **0 model calls, $0.00**.
- T005B real-case generalization is COMPLETE and control-room review PASSED on 2026-10-01. Report: `ops/T005B_REAL_CASE_REPORT.md`.
- T005A (evidence-layer reuse benchmark vs `docushell/ethos`) COMPLETE — **KEEP_CURRENT**, control-room review PASSED on 2026-10-01. Ethos is Apache-2.0 and conceptually close, but v0.6.0 ships macOS/Linux CLI archives only and its Python wheel is a thin wrapper around a caller-supplied `ethos` CLI, so no Windows-runnable path exists without installing a Rust 1.87.0 toolchain; the brief's guardrail required stopping before that install, so Phase 2 was not run. Capability audit also shows Ethos cannot displace T003's fallible-hint search, unique-match/ambiguity rule, cross-page fragment splitting, or per-line highlight runs. Zero T003/T004 code would be removed; 0 model calls, $0.00. Report: `ops/T005A_ETHOS_REUSE_REPORT.md`.

- T005B ran the first genuinely new real case (case id `T005B-01`): a user-supplied secondary passage about Plato's treatment of poetry in 《理想国》 Book X (clue: Stephanus 605B / 607B) traced against a user-supplied 459-page local scan of 柏拉图《理想国》, 郭斌和、张竹明 译 (商务印书馆 1986, read from the scanned colophon page). Result: **`needs_ocr`**, the honest failure state the brief asked for. All 459 pages carry no usable text layer (0 normalized characters; every sampled page is one full-page image with no font resources), and PaperQA2 `Docs.aadd` fails closed with `ValueError: This does not look like a text document`, indexing 0 chunks; the paid query stage was deliberately not run. No evidence, page number or highlight was invented, and the secondary paraphrase is kept out of the source-evidence field. Cost: 0 model calls, $0.00; no new dependency. Regression: T003 15/15, T004 16/16; C04 hashes and mtime untouched. Report: `ops/T005B_REAL_CASE_REPORT.md`.
- T005B confirmed on real material two coverage gaps that T004 had only proven with synthetic fixtures: there is no scan/OCR ingestion path (the stack cannot ingest an image-only source at all), and humanities canonical clues (book/chapter, Stephanus references) have no mapping to the pipeline's PDF page-label hint. A third item — that a secondary paraphrase cannot be literally matched against primary text — is recorded as an untested hypothesis, not a finding.

- T006 Phase 1 control-room review PASSED on 2026-10-01. The shortlist is **OCRmyPDF + RapidOCR**; this is a technical shortlist only, not installation authorization.
- T006 Phase 1 (static OCR reuse scan) COMPLETE on 2026-10-01 — report `ops/T006_OCR_REUSE_REPORT.md`. Nine OCR candidates verified read-only via the GitHub connector and reduced to the two the brief allows: **OCRmyPDF** (text-layer PDF, reuses the existing PaperQA2 + T003 path unchanged; needs Ghostscript + Tesseract + `chi_sim`) and **RapidOCR** (Apache-2.0, pure pip/ONNXRuntime, no system binary, PaddleOCR models converted to ONNX). Docling excluded as an engine host adding a second document representation; PaddleOCR subsumed by RapidOCR's ONNX conversion; MinerU too heavy for this step. The only OCR-capable plugin available is the hosted Adobe Acrobat connector (not embeddable). Corrections recorded: MinerU is Apache-2.0 with additional commercial thresholds (not AGPL); Marker is Apache-2.0. No install, no model download, no system package, no product-code change, 0 model calls, $0.00.

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

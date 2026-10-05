# PROJECT_STATE

Last updated: 2026-10-05 (result layout V3 visual cleanup implemented and regression-green; user visual acceptance remains the unique next gate)

## Project

二流文科生的二手文献引用助手.

## Product principle clarified in Pilot Case 001

D024 is now confirmed: the product exists not only to find citations but to help stop citation errors from propagating. Secondary literature and academic authority are navigation leads, not substitutes for primary evidence. When verification fails or conflicts appear, preserve attribution and provenance rather than hiding the problem by deleting the citation or silently normalizing metadata. Minimum promise: **尽量引用对，不误后来人。**

## Current phase

Gate 0 product definition: CLOSED.

Historical MVP milestone D019 remains accepted. Footnote-first V0.2 remains the active product surface.

The Weber Golden Demo functional target is **PASS**. The project is now in **UI / visual / portfolio-demo packaging**.

Authorized UI Goal:
`ops/UI_RESULT_PAGE_PORTFOLIO_GOAL_2026-10-04.md`.

Implementation reports:
- `ops/UI_RESULT_PAGE_PORTFOLIO_REPORT_2026-10-04.md`
- `ops/UI_RESULT_LAYOUT_V2_REPORT_2026-10-05.md`
- `ops/UI_RESULT_LAYOUT_V3_REPORT_2026-10-05.md`

Current UI status: **RESULT LAYOUT V3 IMPLEMENTED + REGRESSION PASS / USER VISUAL ACCEPTANCE PENDING**.

V3 keeps the V2 desktop 2.5-column interaction but tightens the formal-user presentation: full product name is the main title; the single-PDF source row is compact so bibliography/candidates move into the first screen; the source card removes path-style explanatory copy; edition conflicts are a separate yellow warning card; the right detail panel contains only original-page highlight, corresponding Chinese source text and copyable citations. Normal debug information remains absent. OCR provenance remains a compact badge only when OCR is actually used. No frontend framework or retrieval/model/provider/OCR architecture change was introduced.

The real Weber Golden result remains honestly classified as `multiple_candidates`: 7 localized candidates fall inside the existing plausibility band. The human-reviewed correct passage is the candidate on printed pp.105-106 / PDF pp.111-112, but the UI does not hard-code that known answer or force a unique winner.

Source acquisition, credentials/providers, ranking/retrieval changes and the cand-01 punctuation-tolerant locator fix stay off the current critical path.

## Current status

### What passed in control-room review

- The normal UI visibly implements the three V0.2 blocks.
- Footnote parsing is a distinct deterministic component and cited work vs containing publication are modelled separately.
- The normal no-PDF lookup is routed through parsed/confirmed identity rather than a free-standing broad search.
- Technical/demo controls are collapsed out of the normal flow.
- The existing evidence/highlight pipeline remains reused rather than replaced.
- Codex reported regressions green at delivery: MVP 70/70, T003 15/15, T004 16/16, T006 5/5, source acquisition 98/98, footnote-first 16/16. GitHub has no commit status / Actions run for `9c929012`, so those executions are recorded delivery evidence, not an independent CI rerun by control-room review.

### Acceptance findings — all closed (2026-10-03)

1. **Secondary-page upload on `/identify` — FIXED.** `/identify` now reads
   `secondary_file` with the existing text-layer/RapidOCR helper and carries the
   extracted text through the continuation.
2. **Footnote-image upload on the owned-PDF `/extract` path — FIXED.** `/extract`
   now reads `footnote_file`; the direct-PDF route keeps the navigation clue and
   still never calls `sa.search_all`.
3. **Confirmed bibliographic identity end-to-end — FIXED.** The confirmed
   identity is serialised (`identity_json`) through `/use_found`, the no-PDF ->
   owned-PDF continuation and `/run`; `footnote_parse.compose_citation_metadata`
   composes it with the PDF's own metadata with per-field provenance, kept-visible
   conflicts, and no foreign-work-as-Chinese-citation fabrication.
4. **Insufficient-clue retry — FIXED.** The page now offers an editable footnote
   textarea, a footnote screenshot upload and an owned-PDF upload, and accepts a
   real new clue.

The targeted lookup now also prefers the confirmed Chinese-publication clues
(P1-E). These were small, reversible product defects; no architecture change and
no new provider/dependency/model call was introduced.

The control-room re-review's three browser-flow findings are also closed:

5. **No-PDF page must expose the owned-PDF upload — FIXED.** `render_finder`
   renders a real `multipart/form-data` `primary_file` upload form to `/extract`;
   the rendered path reaches `/run` with the confirmed identity and no second
   `sa.search_all`.
6. **Clearing a parsed field must clear it — FIXED.** `_id_overrides` treats a
   present-but-blank `id_*` as authoritative; `build_identity` clears the field,
   records `用户确认：留空（未识别）` provenance, and drops the parsed title
   variants, so search and citation metadata respect the blank.
7. **Identity-screen edits must survive the direct upload — FIXED.** The direct
   owned-PDF control now shares the editable identity form
   (`formaction='/extract'`); edited values (including blanks) reach the final
   bibliographic metadata/citation, and the route stays offline.

### Verification (0 model calls, $0.00)

`mvp_probes` **70/70**, T003 **15/15**, T004 **16/16**, T006 **5/5**,
`source_acquisition_probes` **98/98**, `footnote_first_probes` **38/38** (16 -> 31
real HTTP-path continuation checks; 31 -> 38 with 7 rendered-browser-path checks
for the three re-review gaps). The single-network-call invariant is preserved.

### Pilot Case 001 — finding fixed (2026-10-03)

The first real thesis case exposed a bounded parser/UX defect: the conventional
note `[德]马克思·韦伯.学术与政治[M].冯克利译.北京:外文出版社,1998:41.` was not
recognized as author + title (the deterministic Chinese parser expected `《…》`),
so `/identify` asked for more clue; retrying with
`[德]马克斯·韦伯,学术与政治` looked like a dead button because the same page
rendered with no explanation.

Fix `ops/PILOT_CASE_001_GBT_FOOTNOTE_FIX_GOAL_2026-10-03.md` is **COMPLETE**
(report `ops/PILOT_CASE_001_GBT_FOOTNOTE_FIX_REPORT_2026-10-03.md`):

- `tools/footnote_parse.py` now parses GB/T 7714-style Chinese notes
  (`[德]作者.题名[M].译者译.出版地:出版社,年份:页码`, plus the short
  `作者,题名` clue) while the `《…》` / quoted parser is untouched; the parser
  extracts the note as written and never silently corrects it from outside
  knowledge (the `外文出版社`/`41` conflict remains a later evidence conflict);
- `tools/mvp_app.py`'s `/identify` now shows an explicit message naming the
  still-missing handles (篇名/书名、作者、DOI、ISBN) when a non-empty retry is
  still insufficient, instead of rendering an indistinguishable page;
- `tools/footnote_first_probes.py` grew 38 -> **47**; new checks fail on the
  `ecbd2c9` baseline.

Regressions rerun green (0 model calls, $0.00): `mvp_probes` 70/70, T003 15/15,
T004 16/16, T006 5/5, `source_acquisition_probes` 98/98, `footnote_first_probes`
47/47. No new provider, credential, dependency, model call or architecture; the
single-network-call invariant and the accepted evidence routes are unchanged.

Control-room review of commits `99c9256` + `dd06878` is **PASS**. Code review
confirmed that the real `[德]作者.题名[M]...年份:页码` fixture reaches the identity
path without silent correction, the shorter `作者,题名` clue is supported, and
insufficient retries now produce visible feedback. GitHub still has no Actions /
commit-status checks for these commits, so suite counts remain Codex local
execution evidence plus independent control-room code review.

### Pilot Case 001 — second real-use finding (2026-10-03)

After the accepted GB/T fix, the exact real citation now reaches the finder.
The finder correctly reports that only weak matches were found, but the normal UI
still renders unrelated OpenAlex open-PDF records with prominent download/use
buttons. This is a D024 safety contradiction: access eligibility currently makes
a record actionable even when bibliographic relevance is below the declared
relevance floor.

Code review shows the current search query also over-relies on the typo-bearing
author + generic title terms. The next bounded fix will:
- make relevance/title anchoring part of actionability;
- prefer title + translator + year as stable search terms without mutating the
  original parsed identity;
- preserve the honest no-match + upload fallback when nothing trustworthy survives.

Reuse scan: keep the current provider stack first. Google Books has the correct
1998 public record but the current anonymous API path is unreliable/rate-limited;
adding a key is a Human Gate. Open Library has public no-key edition APIs but quick
coverage checks did not establish this exact 1998 edition; WorldCat Search API
requires institutional/OAuth access. No new provider is authorized in this fix.

Authorized goal:
`ops/PILOT_CASE_001_SOURCE_RESOLUTION_SAFETY_GOAL_2026-10-03.md`.

### Pilot Case 001 — source-resolution safety fix COMPLETE (2026-10-03)

Report: `ops/PILOT_CASE_001_SOURCE_RESOLUTION_SAFETY_REPORT_2026-10-03.md`.

The bounded fix is **COMPLETE** (D018 pilot defect-fix batch, executed after a
fast-forward to `0f4684c`). It closes the D024 safety contradiction:

- P0-K: actionability now requires **both** evidence eligibility and
  bibliographic relevance — `match_score >= RELEVANCE_FLOOR` plus a real title
  anchor (normalized title match / CJK bigram overlap) or an exact DOI/ISBN
  match. `classify_outcome()` drives every branch from that gate, so the
  top-level verdict and the per-record buttons cannot disagree. Records that
  fail the gate render no download/use affordance, are moved into a collapsed
  `开发者 / 调试：本次未采用的记录` block, and are refused server-side by
  `POST /use_found`.
- P0-L: for a standalone Chinese book the lookup now tries the stable edition
  clue first — the real case becomes `学术与政治 冯克利 1998` — while the
  original parsed fields are never mutated and the author+title query stays as a
  fallback. `identity_anchor()` supplies the confirmed titles + DOI/ISBN.
- P1-M: the empty state plainly says no trustworthy matching candidate was
  found (and that this does not mean the work does not exist), keeping the
  parsed bibliographic bundle and the owned-PDF upload fallback.

Verification (0 model calls, $0.00): `mvp_probes` 70/70, T003 15/15, T004 16/16,
T006 5/5, `source_acquisition_probes` **98 → 106**, `footnote_first_probes`
**47 → 58**. All 19 new checks fail on the pre-fix baseline (the baseline run
actually downloaded the unrelated PDF and aborted). The single-network-call
invariant and the accepted evidence routes are unchanged. No new provider,
credential, dependency, model call or architecture was added; Open Library,
WorldCat and a Google Books key remain deferred.

Live rerun of the same real finder step on the safe build (0 model calls, $0.00):
the query is now `学术与政治 冯克利 1998`, the outcome is honestly
`USER_UPLOAD_REQUIRED`, **no** record renders a download/use action, and all 8
returned records (score 0.00–0.125, including plainly unrelated OpenAlex open
PDFs) are withheld into the collapsed debug list with an explicit reason. The
edition bundle and the owned-PDF upload fallback stay intact. Direct pilot
evidence: the same real case still cannot resolve a trustworthy edition
(Google Books holds the correct 1998 record but the anonymous path returns HTTP
429; the current providers have no zero-friction Chinese edition lookup).

### UNIQUE NEXT

**User visual/product acceptance of the result-page UI draft.**

Open the real Weber Golden Demo preview and review the normal result hierarchy. The draft is regression-green but is **not** yet portfolio/demo accepted.

Human Gate questions:
- Is the page understandable to a non-technical humanities user?
- Is the evidence / page / edition-conflict hierarchy right?
- Is the neutral academic/product visual baseline acceptable?
- Does the real `multiple_candidates` experience expose a new product need for explicit user confirmation/selection?

Do not merge the UI branch to `main`, expand the whole application UI, or change retrieval/ranking to make the Golden case look cleaner before this review.


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

# MVP CANDIDATE REPORT — 2026-10-02

Status: **MVP candidate delivered and verified. NOT accepted as MVP COMPLETE.**
The final acceptance decision belongs to control-room review plus the user's
milestone decision; Codex does not make it.

Brief executed: `ops/MVP_PRODUCTIZATION_GOAL_2026-10-02.md`.
Durable adoption in force: **D017** (RapidOCR as an optional scan-ingestion
component; text-layer path stays default).

## 1. Result in one paragraph

The accepted retrieval/evidence experiments are now a runnable product instead
of a set of experiment scripts. One canonical entry point
(`tools/mvp_app.py`) drives one shared backend contract (`tools/mvp_pipeline.py`):
it takes a secondary-source passage (pasted text, uploaded PDF, or uploaded
photo) plus optional fallible hints, resolves a local primary source, decides
how that source can be searched at all, ranks candidate passages with a local
embedding (zero paid calls), localizes them to exact page geometry with the
proven T003/T004 evidence layer, and renders a compact result with copyable
original text, highlighted original-page images, PDF page provenance,
metadata-honest citations and an explicit four-way result state.

Two real routes and one real honest failure were exercised through that entry
point. Whole task cost: **0 model calls, $0.00**.

## 2. Canonical launch command

```powershell
$env:PQA_HOME = $PWD
.\.venv\Scripts\python.exe tools\mvp_app.py
```

Open <http://127.0.0.1:8765>. Headless single run:

```powershell
.\.venv\Scripts\python.exe tools\mvp_app.py --run-once `
  --secondary-text "在《理想国》第十卷，苏格拉底竟扬言要将诗歌逐出城邦（605B、607B）。" `
  --source T005B-01 --hints "Stephanus 605B / 607B"
```

The app binds to loopback only, has no accounts, and performs no external
upload. Runs, page images and OCR text stay under the git-ignored
`data/private/`.

## 3. Stage 0 — reuse scan for the product surface

Order walked before writing any UI code:

1. **Current repo.** `tools/t006_demo.py` and `tools/t006_ocr_pipeline.py`
   already generate a self-contained HTML evidence report with relative image
   references, status chips, warnings and citations from real artifacts. That
   rendering approach is reused, not replaced.
2. **Current environment.** The verified `.venv` has no web framework
   (no Streamlit / Gradio / Flask / FastAPI). Everything needed for a local
   form + result page is in the standard library.
3. **Native/installed skills.** The bundled `pdf` and `documents` skills cover
   rendering and document authoring, not a local interactive product surface.
4. **Lightweight local UI options.** Streamlit and Gradio would each add a new
   dependency tree (and Gradio a JS frontend) for one form and one result page;
   a React/Vite stack is explicitly out of scope in the brief.

Decision: a **stdlib-only `http.server` local web app** with an HTML/CSS result
view, plus a `--run-once` headless mode for scripts and probes. It adds no
dependency, no build step, no auth and no deployment surface, which is smaller
than every alternative that would materially reduce code.

## 4. Stage 1 — reproducible environment

- Interpreter recorded and verified: **CPython 3.11.9 (Windows)**
  (deliberately not the machine-default Python 3.14).
- `requirements.txt`: curated, pinned direct dependencies with a documented
  boundary between the retrieval/evidence stack and the optional OCR extras.
- `requirements.freeze.txt`: exact `pip freeze` export of the verified machine
  (118 packages) for bit-for-bit reproduction.
- Local caches are never committed: `.venv/`, `.pqa/indexes/`, `.pqa/cache/`,
  `data/private/` stay ignored; no model binaries are tracked.
- Verification performed: `pip check` → *No broken requirements found*;
  all 9 pins in `requirements.txt` match the installed versions exactly.
- Not performed: a from-scratch `pip install -r requirements.txt` in a fresh
  venv. It needs a large download (torch and friends) and a stable network, and
  it is the one item in this report that is **unverified**; the manifest and the
  freeze file are consistent with the environment in which every result below
  was produced.
- The first query against a text-native book parses it once and caches the page
  text under `data/private/mvp_cache/parse/`. Re-parsing 1800 pages costs about
  131 s; the cached parse is instant.

## 5. Stage 2 — real product entry point

`tools/mvp_pipeline.py` is the shared contract; `tools/mvp_app.py` is the
surface. Routing:

| Source condition | Route |
| --- | --- |
| PDF with a usable text layer | text-layer path (accepted T003/T004 evidence chain) |
| image-only scan + RapidOCR cache present | OCR path (D017 optional fallback) |
| image-only scan, no cache, `ocr_mode=auto` | honest `insufficient_source` |
| image-only scan, `ocr_mode=force` | OCR the whole scan first (slow, explicit) |
| image-only scan, `ocr_mode=off` | honest `insufficient_source`; an existing cache is *not* used |

Inputs: pasted text, uploaded secondary PDF, uploaded image/photo, optional
free-form hints. A secondary PDF uses its text layer when it has one, otherwise
its first pages are OCR'd and the result is labelled as OCR. Images are read
with the adopted RapidOCR engine.

Multi-item pages: a simple, documented splitter (blank lines, then sentence-final
punctuation) proposes items with checkboxes, and the confirm step always lets the
user edit the text by hand before retrieval. This is the brief's "simplest honest
fallback" — no robust multi-item detection was invented, and the gap is recorded
in §11.

Hints stay fallible: they only add candidates (a second retrieval pass whose
hits are re-scored against the *secondary passage*), never filter out a
candidate the plain passage produced, and never override contradictory page
evidence.

## 6. Stage 3 — result experience

Compact default view, progressive disclosure per candidate
(`<details>`): retrieval rank, local similarity, PDF page, printed page
(`未确认（不会用 PDF 页号顶替）` unless actually confirmed), retrieval page
label, evidence origin, copyable original text, highlighted original-page image,
known bibliographic metadata, copyable footnote and reference-list citations,
unresolved fields and warnings.

The four PRODUCT_V0_1 failure states are distinguished and never collapsed:
`evidence_found`, `multiple_candidates`, `no_corresponding_passage`,
`insufficient_source`. The state rule is deterministic and visible: a located
candidate is *plausible* when its local similarity is inside a 15 % relative
band of the best hit; multiple plausible candidates are shown side by side
instead of forcing one winner.

OCR results always carry a visible "machine reading of the page image, verify
against the page" notice and list `ocr_text_verification` as unresolved. **No
character-accuracy percentage is published anywhere.**

## 7. Stage 4 — two real routes and one real honest failure

All runs below go through the product entry point and the same result contract.

| | **Route A — text layer** | **Route B — scan** |
| --- | --- | --- |
| Command | `mvp_app.py --run-once --source C04` | `mvp_app.py --run-once --source T005B-01 --hints …` |
| Source | 韦伯《经济与社会》第一卷（阎克文译，2019），1800 页文本层 PDF | 柏拉图《理想国》（郭斌和、张竹明译，1986），459 页影印扫描本 |
| Input | the real historical 38-character noisy query | the real T005B-01 secondary passage + Stephanus 605B/607B hint |
| Route taken | `text_layer` | `ocr` (459 cached RapidOCR pages) |
| Chunks | 5844 | 846 |
| Time | parse 0 s (cached) + index 164.1 s + retrieve 0.1 s + evidence 5.8 s | index 23.4 s + retrieve 0.2 s + evidence 3.0 s |
| Candidates | 10 | 15 (10 from the passage, 5 hint-only) |
| Located with geometry | **10/10** | **15/15** |
| Highlighted original pages | 11 | 27 |
| Result state | `multiple_candidates` | `multiple_candidates` |
| The known target region | gold passage → **PDF page 109, rank 3** | Book X poetry expulsion (Stephanus `607`) → **PDF pages 417–418, rank 7** |
| Model calls / cost | **0 / $0.00** | **0 / $0.00** |

Honest failure through the same entry point, on real material:

| | Failure route |
| --- | --- |
| Command | `mvp_pipeline.py --source T005B-01 --ocr-mode off` |
| Source state | 459 pages, **0 pages with a usable text layer**, OCR deliberately off |
| Result | `insufficient_source` — "当前来源无法提供足够的可检索一手文本", 0 candidates, 0 highlights, blocker `ocr_disabled_by_request` |
| `result.json` | written, so the honest failure is viewable in the product surface like any other result |

Route A reproduces the accepted historical truth: the gold passage still
resolves to **PDF page 109** and the cross-page candidate still splits across
**pages 130–131**, with all private artifacts untouched (hashes in §9).

## 8. Stage 5 — product cleanup

- **Page furniture.** A deterministic, display-only rule hides repeated margin
  noise (at most two characters, or at most six characters with no Chinese
  ideograph, on ≥2 % of pages). Measured on the T005B-01 OCR text it hides the
  OCR fragments of the vertical running head and margin numerals/Latin letters,
  while repeated dialogue stamps (`格：是的。`) and running titles (`理想国`,
  `第十卷`) are explicitly preserved because they can carry meaning. The
  retrieved `original_text` and the highlight geometry are never modified, and
  every hidden token is reported to the user.
- **Experimental language.** The user-facing surface says MVP candidate; the
  T006/T004 experimental notices are gone from the product pages.
- **Broken paths.** Image references are resolved relative to the report and
  served through an in-app endpoint that refuses any path outside the run
  directory (verified: 403).
- **Setup/start instructions.** Rewritten root `README.md` with one canonical
  launch command, the clean-install path, the registry workflow and the
  verification commands.
- Not touched (per the brief): branding, animation, visual design, accounts,
  deployment, universal acquisition, paper writing.

## 9. Stage 6 — tests and integrity

| Suite | Result |
| --- | --- |
| `tools/mvp_probes.py` (new product entry point) | **44/44 passed** in 13.8 s |
| `tools/t003_regression_probes.py` | **15/15 passed** |
| `tools/t004_regression_probes.py` | **16/16 passed** |
| `tools/t006_ocr_probes.py` | **5/5 passed** |
| Web surface smoke (live server) | `GET /` 200 with the input form; `POST /extract` 200 with the confirm step; `/asset` out-of-run path → 403 |
| Dependency smoke | `pip check` clean; all 9 `requirements.txt` pins match the installed environment |

The new probes are zero-cost and self-contained: they use generated synthetic
PDFs (`data/private/mvp_probes/`, git-ignored and deleted from the repo's
tracked tree) for the two end-to-end routes, so no private or copyrighted
material is needed and none is committed. Coverage includes: input handling for
pasted text / text file / unsupported upload; the item splitter; all four result
states; the plausibility band; display-only furniture cleanup (evidence
untouched); hint merging and re-scoring; multipart and urlencoded form parsing
with duplicate checkbox fields; the asset path guard including traversal;
HTML escaping of candidate text; citation honesty with missing metadata;
registry integrity; a synthetic text-layer run (locates the passage, writes the
highlight, 0 model calls, refs stay private); a synthetic image-only run
(`insufficient_source`, no geometry); and `ocr_mode=off` refusing an existing
OCR cache.

Integrity of the accepted artifacts, re-verified after all runs:

| Artifact | sha256 | Status |
| --- | --- | --- |
| `data/private/C04/pqa_corpus/C04.pdf` | `d3e3b0687c70fb8db9179d40b2d666ed3536bcfa14da3602a78fdc5c791b48c1` | unchanged |
| `data/private/C04/results/m1e1_c04_20261001-113927.json` | `68238b48e348b148457e59409e84a8003ff244e8b4ee2a144b4a9461e8bbc335` | unchanged |
| `data/private/T005B-01/source/T005B-01_source.pdf` | `4d8d8c8a9c29ca24edaba68ac418aa68e9b8739e2fe47004c34b0cbea33a739b` | unchanged |

Git hygiene: `git ls-files data/private` is empty; every new artifact lives
under the ignored tree.

## 10. PRODUCT_V0_1 requirement matrix

| Requirement (PRODUCT_V0_1) | Status | Evidence / reason |
| --- | --- | --- |
| Product name 二流文科生的二手文献引用助手 | MET | used in the app, README and report |
| secondary literature → primary evidence, no paper writing | MET | the pipeline returns evidence objects; no essay or literature-review feature exists |
| Evidence first; uncertainty allowed and explicit | MET | four result states, per-candidate status, warnings, unresolved fields |
| Input: pasted text | MET | `input/pasted` probe |
| Input: uploaded secondary PDF | MET | text layer when present, otherwise OCR of the first pages |
| Input: uploaded image / photographed page | MET | RapidOCR path, labelled as OCR |
| Optional free-form hints field | MET | hint pass adds candidates only |
| Hints/footnotes are never authoritative | MET | hints cannot remove a candidate or override page evidence |
| Multi-item detection with select / select-all / manual correction | PARTIAL | simple splitter + per-item checkboxes + editable text; the splitter is a rule, not a robust detector (no paid model was spent to invent one) |
| Evidence priority order (page evidence > passage semantics > clues > memory) | MET | page geometry comes from the source; clues only affect recall |
| Author-agnostic scope, coverage by available sources | MET | registry is user-extensible; Weber is evaluation material, not a whitelist |
| Honest "current sources can't verify" instead of implying non-existence | MET | `insufficient_source` wording says exactly that |
| Copyable Chinese original text | MET | `original_text`/`display_text` in a read-only textarea with a copy button |
| Original-page screenshot with highlight | MET | 11 (route A) and 27 (route B) PNGs, all geometry-checked by the T003 layer |
| Page number | MET (PDF) / PARTIAL (printed) | PDF sequence page always; printed page stays `未确认` because none was confirmed |
| Known bibliographic metadata only | MET | metadata table + `metadata_origin`; `_citations_are_confirmed` regression |
| Copyable footnote + reference-list citation | MET | both shells per candidate; byte-equal to a page-less rebuild when no printed page is confirmed |
| Do not invent missing metadata | MET | missing author/title → no citation string at all, plus `unresolved_fields` |
| Multiple candidates, no forced winner | MET | 10 and 15 candidates retained; `multiple_candidates` state |
| Multiple editions / translations side by side | PARTIAL | mechanism supports several registered sources per query, but only one edition per work is registered locally, so it is unproven on real material |
| Progressive disclosure | MET | candidate list + `<details>` expansion |
| AI judgment needed but output spends no tokens on long essays | MET | default retrieval is embedding-only, 0 model calls, no interpretive text |
| Deep misquotation analysis deferred/on-demand | NOT MET / deferred | not implemented, as the brief allows; no on-demand hook yet |
| Four failure states distinguished | MET | classification + probes per state |
| Never manufacture a match | MET | localized only on verbatim occurrence; unmatched/ambiguous candidates are kept without geometry |
| MVP boundary: limited sources acceptable | MET | registry + local paths; no universal acquisition |
| OCR text labelled, page-image verification warning, no accuracy claim | MET | OCR notice on every OCR surface; `ocr_text_verification` unresolved; no percentage published |
| Printed page never replaced by a PDF page | MET | `printed_page_numbers` always empty; citations rebuilt page-less and compared |

## 11. MVP candidate acceptance bar

| Bar item (from the brief) | Status | Evidence |
| --- | --- | --- |
| A fresh local user can set up and launch from committed instructions | PARTIAL | README + `requirements.txt` + `requirements.freeze.txt` are committed and `pip check` is clean; a from-scratch network install was not executed (§4) |
| The canonical interface accepts a real secondary input and a real primary source resource | MET | Route A and Route B both run with real inputs through `tools/mvp_app.py` |
| Text-native and scan routes both work through the same surface/contract | MET | both write the identical `result.json` contract; same renderer; same status/state vocabulary |
| At least one real result shows copyable primary text + page image/highlight + provenance + citation | MET | Route A gold on PDF page 109; Route B Stephanus 607 region on PDF pages 417–418 |
| Honest failure states remain distinguishable | MET | real `insufficient_source` on the 459-page scan with OCR off, written as a viewable result |
| No private/copyright source content is committed | MET | `git ls-files data/private` empty; probes use synthetic fixtures |
| Regressions stay green | MET | 44/44, 15/15, 16/16, 5/5 |

**Conclusion: the brief's MVP candidate bar is met, with one explicitly
unverified item (from-scratch dependency installation). The result is an MVP
candidate. It is not MVP COMPLETE: that needs control-room review and the user's
milestone acceptance.**

## 12. Cost

Whole task: **0 model calls, $0.00**. No paid/API OCR, no elevation, no
system-wide change, no Docker/WSL/CUDA, no external upload. The only network
access used was the run-environment package/model cache already present and the
Git push of the checkpoints.

## 13. Known gaps and deferred items

1. **Robust multi-item detection** on a page with several quotations — currently
   a documented rule plus manual confirmation.
2. **Multiple editions/translations of the same work shown together** — the
   registry allows it but no second edition is registered, so it is unproven.
3. **From-scratch dependency install** — manifest validated against the verified
   environment, not by a clean download.
4. **First-run cost on a long book** — parsing 1800 pages ≈131 s and embedding
   5844 chunks ≈160–420 s depending on machine load; an in-process index cache
   makes repeat queries in the same session fast, but a restart pays the
   embedding cost again.
5. **Ranking stability** — Route A still puts the gold passage at rank 3 and
   Route B at rank 7 with the free local embedding; the LLM-reranked path
   (`tools/t004_backend_slice.py`) remains available but is not wired into the
   product entry point because it spends money.
6. **OCR accuracy** — still no certified human transcription; unchanged from
   T006 and still owed before any accuracy claim.
7. **Printed page vs PDF page mapping policy** — still unresolved and still a
   Human Gate; the product currently reports the PDF page and marks the printed
   page unresolved.
8. **Page-furniture handling inside highlight spans** — only the displayed text
   is cleaned; highlight geometry still covers the raw detected span.

## 14. Recommended NEXT (one)

**Human Gate + control-room review of this MVP candidate**, deciding in one
pass: accept or reject the candidate as the MVP milestone; whether to fund the
LLM-reranked retrieval mode inside the product entry point; and whether to
commission the two owed verification items (a certified human transcription of
the frozen OCR sample, and a second real scan case) plus the printed-page →
PDF-page mapping policy.

## 15. Exact commits

| Checkpoint | Commit |
| --- | --- |
| Product entry point, pipeline, probes, manifest, README | `817f50c` |
| Honest-failure results + `ocr-mode=off` semantics | `8120c9a` |
| This report + ops/AGENTS state update | the commit that adds this file (reported in the handing-off message) |

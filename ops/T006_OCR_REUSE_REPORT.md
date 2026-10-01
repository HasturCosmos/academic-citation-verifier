# T006 — OCR reuse benchmark report

Status: **Phase 1 (static) COMPLETE. Phase 2 (bounded runtime benchmark)
EXECUTED on a frozen sample. Experimental OCR integration validated on real
material.** No durable OCR adoption is proposed here — that stays a human
decision.

Brief: `ops/T006_OCR_REUSE_BENCHMARK.md`. Executed under the authorized batch
`ops/OVERNIGHT_GOAL_2026-10-01.md` (the user passed the T006 Phase 2 human gate
on 2026-10-01).

Dates: Phase 1 2026-10-01; Phase 2 runtime work 2026-10-01 → 2026-10-02.

Everything committed by this task is code and documentation. All OCR text, page
images, caches and evidence objects live under the git-ignored `data/private/`.

## 1. Static comparison

Every row is a read-only 2026-10-01 read of the GitHub repository API or of a
file in the repository. Stars and last-push are recorded so the maintenance
claim is checkable, not assumed.

| # | Candidate | License (verified) | Stars | Last push | Chinese printed text | Windows install | Page provenance | Added infrastructure |
| - | --------- | ------------------ | ----- | --------- | -------------------- | --------------- | --------------- | -------------------- |
| 1 | ocrmypdf/OCRmyPDF | MPL-2.0 | 34,913 | 2026-09-29 | via Tesseract `chi_sim` | yes, but needs Ghostscript + Tesseract binaries | one-to-one, positioned text layer written into the PDF | 2 system binaries + `chi_sim.traineddata` |
| 2 | RapidAI/RapidOCR | Apache-2.0 | 8,022 | 2026-10-01 | native (PaddleOCR models in ONNX; README: "default support for Chinese and English") | `pip install rapidocr onnxruntime`; no system binary, no torch | per-page render → per-text-line quadrilateral boxes | pip packages + small model weights |
| 3 | docling-project/docling | MIT | 68,254 | 2026-10-01 | via Tesseract / EasyOCR / RapidOCR backends | pure pip | page + bbox in its own document model | pip + models + a second document representation |
| 4 | PaddlePaddle/PaddleOCR | Apache-2.0 | 90,490 | 2026-09-16 | strongest Chinese ecosystem | CPU wheels only | boxes + PP-Structure layout | paddlepaddle runtime + larger models |
| 5 | datalab-to/surya | Apache-2.0 | 21,434 | 2026-09-11 | 90+ languages | pip + torch | layout / reading order / OCR boxes | torch inference |
| 6 | datalab-to/marker | Apache-2.0 | 40,146 | 2026-09-13 | via Surya | pip + torch | PDF → markdown/JSON, page level | Surya + torch |
| 7 | opendatalab/MinerU | Apache-2.0 + additional terms | 80,944 | 2026-09-30 | native | pip, GPU-preferred | PDF → markdown/JSON with layout | large model downloads |
| 8 | deepseek-ai/DeepSeek-OCR | MIT | 23,925 | 2026-01-27 | native | needs GPU-class local or remote inference | text/markdown, no guaranteed boxes | VLM weights or API spend |
| 9 | tesseract-ocr/tesseract | Apache-2.0 | 76,783 | 2026-09-28 | `chi_sim` data pack | installer + separate `traineddata` | word/line boxes via TSV/hOCR | 1 system binary + data |

Reuse-gate steps 1–4 were also checked: the repository has no OCR path (the
T003 adapter needs a real text layer and fails closed); the bundled `pdf` skill
renders pages with Poppler but performs no recognition; the only OCR-capable
plugin available is the hosted **Adobe Acrobat** connector, which cannot be
embedded in a self-hosted product; no installable skill was preferable.

### 1.1 Local environment facts (measured, zero cost)

- Project `.venv`: Python 3.11.9.
- **No OCR binary on `PATH`**: `tesseract`, `gswin64c` and `magick` are absent.

### 1.2 Corrections to earlier notes

- **MinerU is not AGPL.** Its `LICENSE.md` reads "MinerU is licensed under
  Apache License 2.0 and is subject to the additional terms below"; the added
  terms require a separate commercial licence only above 100M MAU or USD 20M
  monthly revenue, plus an attribution obligation for online-service use.
- **Marker is Apache-2.0**, verified from its `LICENSE` file.

## 2. Shortlisted runtime candidates

The brief allows at most two runtime candidates, and exactly two were carried
into Phase 2:

1. **OCRmyPDF** (`--language chi_sim`) — the only candidate whose output would
   feed the proven PaperQA2 + T003 path *unchanged*, because it writes a
   bounding-box-positioned text layer into the PDF. Outcome: **BLOCKED_INSTALL**
   (§4.1).
2. **RapidOCR** (`pip install rapidocr onnxruntime`) — Apache-2.0, CPU-only
   ONNXRuntime, no system binary, no torch; its own README states the models are
   PaddleOCR models converted to ONNX. Outcome: benchmarked and validated
   (§4.2–§4.9).

Not shortlisted, reasons unchanged from Phase 1: **Docling** (engine *host* that
would add a second document representation), **PaddleOCR** (subsumed by its own
ONNX conversion; remains the named fallback), **MinerU** (heavier than this step
needs). Recorded options: Surya/Marker, DeepSeek-OCR, bare Tesseract.

## 3. Benchmark sample (frozen before any engine ran)

The sample was fixed and its rendered artifacts hashed **before** any OCR engine
executed, so it cannot have been tuned to a winner.

- source: `data/private/T005B-01/source/T005B-01_source.pdf`
  (459 pages, sha256 `4d8d8c8a…a739b`, unchanged);
- fixed pages (1-based PDF): **1, 3, 10, 30, 200, 420** — the three
  already-rendered/identified T005B front-matter pages plus three representative
  body pages (第一卷 printed 19, 第五卷 printed 189, 第十卷 printed 409);
- render: 300 dpi via PDFium `page.render`;
- per-page PNG sha256 recorded in `data/private/T006-01/sample_manifest.json`;
- extracted sample PDF sha256
  `3f7a6b5a70a78c12eb905a7ffd266853bbdfa3a25f1e95ace1e4ee28f9916bfd`;
- ground truth: **no certified human transcription exists**, so no CER or
  accuracy percentage is claimed anywhere in this report. §4.3 records a bounded
  visual cross-check and states its method and limits. The secondary paraphrase
  was never used as primary text.

## 4. Measured results

### 4.1 OCRmyPDF — `BLOCKED_INSTALL`

The Python package installs project-locally (`ocrmypdf` 17.13.0), so the question
was whether its two system binaries can be obtained **without elevation or broad
system modification**. Measured answer: no.

```
$ python -m ocrmypdf --language chi_sim --output-type pdf --verbose 1 sample.pdf out.pdf
17.13.0
Did not find Ghostscript in registry key HKLM\SOFTWARE\Artifex\GPL Ghostscript
Did not find Tesseract in registry key HKLM\SOFTWARE\Tesseract-OCR
Running: ['tesseract', '--version']
The program 'tesseract' could not be executed or was not found on your system PATH.
    choco install tesseract
Could not find program 'tesseract' on the PATH
EXIT=3
```

- `tesseract`, `gswin64c` and `magick` are absent from `PATH`.
- `winget` and `scoop` are not installed; the only package manager present is
  **Chocolatey**, whose installs are machine-wide and require administrator
  elevation.
- OCRmyPDF's own suggested remedy (`choco install tesseract`) is therefore an
  administrator action, which the overnight brief forbids without a further
  human gate.

Per the brief ("record `BLOCKED_INSTALL` for that candidate and continue with
RapidOCR"), OCRmyPDF was not pursued further and its behaviour on this facsimile
remains unmeasured. A portable route (e.g. micromamba installing Tesseract +
Ghostscript into a project-local environment) exists in principle but would add a
second package manager — a broader change than this bounded benchmark
authorized — so it is recorded as an option, not executed.

### 4.2 RapidOCR — frozen-sample results

`rapidocr` 3.9.2 + `onnxruntime` 1.30.0. The three ONNX models
(`PP-OCRv6_det_small`, `ch_ppocr_mobile_v2.0_cls_mobile`, `PP-OCRv6_rec_small`)
**ship inside the wheel** — the log reports "File exists and is valid", i.e. no
model download was needed at any point.

| PDF page | OCR lines | margin tokens | body lines | chars | body chars | seconds | mean line score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | 0 | 3 | 22 | 22 | 2.04 | 0.971 |
| 3 | 17 | 0 | 17 | 158 | 158 | 9.05 | 0.977 |
| 10 | 4 | 1 | 3 | 64 | 62 | 6.71 | 0.988 |
| 30 | 29 | 3 | 26 | 501 | 497 | 10.79 | 0.996 |
| 200 | 28 | 3 | 25 | 431 | 424 | 9.80 | 0.998 |
| 420 | 27 | 2 | 25 | 416 | 412 | 9.60 | 0.996 |
| **total** | **108** | **9** | **99** | **1,592** | **1,575** | **48.0** | median 0.992 |

Recognition is dense and well aligned: every body page yielded its full line
count, and mean per-line confidence on body pages is 0.996–0.998.

### 4.3 Character-level cross-check — method and limits

No independent ground truth could be produced safely here: the scan has no text
layer, using one OCR engine's output as another's truth is explicitly forbidden,
and no certified human transcription was available.

What was done, and what it is worth:

- the six frozen page images were read directly at high resolution and compared
  line by line against the OCR output;
- this is an **agent visual comparison**, not a certified transcription, so it is
  reported as observed discrepancies rather than as an accuracy percentage;
- no CER or character-accuracy number is claimed.

Observed discrepancies across the 99 body lines of the six sample pages:

| kind | count | where |
| --- | --- | --- |
| genuine character substitution | 1 | PDF p1 display type: 名**若**丛书 for 名**著**丛书 (line score 0.955) |
| punctuation substitution | 1 | PDF p30 line 3: `坏：` for `坏!` |
| punctuation *width* only (fullwidth vs halfwidth) | a few | e.g. `苏：问题是：` for `苏：问题是:` on p200 |
| bracket variant | 2 | `[古希腊〕` / `【古希腊〕` for `〔古希腊〕` on p1/p3 |
| margin token merged into an adjacent body line | 3 | p30 `…因此，我的339`; p200 `…动机)裸B`; p420 `…最大报酬'TC` |
| header split with a dropped character | 1 | p30 running head `第 一 卷` → `第` + `卷` (`一` lost); p420 read correctly as `第十卷` |

Everything else matched, including long dense paragraphs, dialogue markers
(`苏：`/`格：`/`色：`), the 〔惊讶地看着苏格拉底〕 stage direction, quotation
marks and the colophon's edition data.

Interpretation: for ordinary printed Chinese body text this engine is essentially
correct; residual risk concentrates on stylised display type, punctuation width,
and margin tokens sharing a baseline with body text.

### 4.4 Reading order

Measured on the frozen sample and confirmed again on the full run:

- body text is returned in correct reading order, top to bottom, including
  wrapped lines and dialogue paragraphs;
- the running head's page numbers come back as their own lines (`19`, `189`,
  `409`);
- margin canonical markers come back as their own short lines (`B`, `E`, `D`,
  `339`, `457`) at their real geometry — this is what makes §4.9 possible;
- two failure modes are recorded honestly: a margin token sharing a baseline with
  body text can be merged into that line, and a spaced running head can be split
  with a dropped character.

Consequence for matching: `t003_evidence_localize` matches whitespace-normalised
text, so an inserted margin token inside a passage makes an exact match fail. In
practice this does **not** break the product flow, because retrieval reads the
same OCR text that localization searches — a retrieved chunk is verbatim OCR
text and therefore matches exactly. It does mean a quotation hand-copied from the
printed layout may not match character-for-character across a margin marker.

### 4.5 Page provenance and geometry

- provenance: each page is OCR'd independently and the page number is carried on
  every line record, so a retrieved chunk keeps a `scan pages N-M` label and
  resolves back to exact PDF pages; the full run processed 459/459 pages with no
  page-index loss.
- geometry: the OCR pixel→PDF-point conversion was verified as the exact inverse
  of the renderer transform (`coordinate_round_trip`, worst error 0.25 pt over
  four probe points at 144 dpi).
- highlight verification: the localized fragment on the real scan produced one
  highlight run covering exactly the intended printed line; the rendered
  highlight was inspected visually and matched the source line character for
  character. `geometry_ok` was true with `clipped_runs = 0` and ink present
  inside the run.
- the unchanged T003 rules still hold: repeated text yields `ambiguous` with
  **no** highlight, and a page with no OCR cache entry yields `needs_ocr` with no
  geometry.

### 4.6 Compatibility with the retrieval and evidence stages

This is the decisive result for reuse — the experimental path reuses every proven
component instead of forking a pipeline:

| stage | component used | change required |
| --- | --- | --- |
| OCR text → chunks | upstream `paperqa.readers.chunk_pdf` with the pinned `chunk_chars 400 / overlap 100` | none |
| chunks → candidates | upstream `Docs.aadd_texts` + `Docs.retrieve_texts` with the pinned local embedding `st-BAAI/bge-small-zh-v1.5` | none |
| candidates → evidence | unchanged `t004_backend_slice.build_evidence_object` | none |
| localization, fallible-hint search, ambiguity rule, cross-page split, highlight runs, geometry checks | `t003_evidence_localize` | three overridden methods (`page_text`, `page_entries`, `page_has_text_layer`) in one new subclass |

The pipeline ran end to end on the real 459-page scan:

- model calls **0**; cost **$0.00** (retrieval is embedding-only; the LLM
  answer/rerank stage was deliberately not used);
- candidate objects carry the same fields as T004 plus `evidence_origin: "ocr"`
  and an `ocr_text_verification` unresolved field;
- outputs: `ocr_candidates.json`, `evidence_objects.json`, `run_summary.json`,
  `evidence_report.html`, highlighted page images.

### 4.7 Runtime, resources and disk

- benchmark sample (6 pages, 300 dpi): 48.0 s of recognition, no model download,
  model load 0.37 s;
- steady state: **≈9.5 s per page** at 300 dpi on this machine, single process,
  ONNXRuntime CPU; low-ink pages (running head only) drop to 2–7 s;
- full 459-page pass: §4.8;
- disk: rendered page PNGs dominate at ≈0.84 MB per 300-dpi page (≈385 MB for
  the facsimile) plus ≈7 MB of per-page JSON. This is cache, not product output,
  and it is git-ignored; a production version would not persist the PNGs.

### 4.8 Full-document run (459 pages)

The whole facsimile was OCR'd once at 300 dpi, single process, ONNXRuntime CPU,
into the resumable per-page cache:

| metric | value |
| --- | --- |
| pages OCR'd | **459 / 459** |
| pages with no usable text (<20 chars) | **0** |
| total recognised characters | **239,966** |
| page char count: median / min / max | 518 / 22 / 1,446 |
| wall clock (render + recognise + cache write) | **3,557.8 s ≈ 59.3 min** |
| sum of recognition time only | 3,311.1 s |
| per-page recognition: mean / median | 7.21 s / 8.91 s |
| cache on disk (git-ignored) | **399.4 MB** (≈385 MB PNG + ≈7 MB JSON) |

The long tail is not flat text: the 译名对照表 (pp. 438–445) returns 70–84
lines per page and the 索引 (pp. 447–456) returns 88–152 short lines per page,
which is why per-page recognition time is much less than per-page layout volume.
**Not one page failed**, so the document-level `needs_ocr` of T005B is fully
replaced by searchable text for this source.

### 4.9 Margin canonical clues are recoverable (bounded measurement)

T005B recorded a second real gap: a canonical location clue (Stephanus
`605B`/`607B`) had no mapping to this pipeline's PDF-page hint. The 商务印书馆
1986 facsimile prints Stephanus page numbers and A–E section letters in the outer
margin, and the OCR returns them as their own short lines with real geometry.

Measured over the OCR cache at zero extra model cost
(`tools/t006_margin_scan.py`):

| metric | value |
| --- | --- |
| pages scanned | 459 |
| OCR text lines | 14,265 |
| standalone token lines | 1,388 |
| token lines outside the body column (x ≈ 368–2,038 px at 300 dpi) | **556** |
| margin 3-digit Stephanus-like numbers | **75** |
| margin A–E section letters | **444** |
| observed numeric range | **328 – 663** (the Republic runs 327a–621d, so this is the Stephanus series, not a page-number series) |
| case clue `605` | PDF page **415**, left margin, standalone line, score 1.00 |
| case clue `607` | PDF page **418**, right margin, standalone line, score 1.00 |

Both case targets were then verified against the page images: the printed `605`
really sits in the left margin of PDF page 415 and the printed `607` really sits
in the right margin of PDF page 418, at the OCR-reported coordinates. The other
`605`/`607` string matches in the document (pp. 438–445) fall inside the name
index and are **not** margin markers, which is exactly the kind of false positive
this measurement has to be read with.

This is a **measurement, not a shipped feature**: the mapping is inferred from
geometry and is reported together with the page images so a human can verify it.
It is recorded as a promising route for the canonical-clue gap, not as a
confirmed resolution.

### 4.10 End-to-end result on the real case (T005B-01)

The case that produced the honest `needs_ocr` failure in T005B was re-run
through the experimental path — same source scan, same secondary passage, same
metadata, no new acquisition:

| stage | T005B (before) | T006 experimental (now) |
| --- | --- | --- |
| text-layer scan | needs_ocr (0/459 pages) | unchanged — still 0/459 |
| candidate retrieval | not possible | 10 candidates from OCR text, local embedding only |
| evidence | none, correctly | 10/10 `located` with verified highlight geometry |
| model calls / cost | 0 / $0.00 | 0 / $0.00 |

The retrieved set contained the case's actual region. The single most relevant
chunk is **rank 7**, resolving to PDF pages **417–418** — the Book X passage in
which the translator's text says the city was right to expel poetry, on the page
whose right margin carries the verified Stephanus `607` marker. Rank 10 resolves
to PDF pages 419–420 (also Book X, 7 occurrences of 诗). Ranks 1 and 3 landed on
PDF pages 397–398, the mimesis discussion at the opening of Book X — topically
adjacent but not the cited location.

Honest reading: **Top-1 miss, Top-10 hit.** This reproduces T001/T004's finding
that the embedding-only stage ranks the true region mid-list; the delivery
improvement here is that the region is now *reachable at all*, with page
provenance and a verified highlight that a human can check. The ranking itself
was not tuned and no LLM rerank was used, because that would have required a paid
call.

The generated HTML report for this run is
`data/private/T006-01/demo/demo_report.html`, with stage 1 (`needs_ocr`) and
stage 2 (OCR evidence) side by side. A known limitation reappeared and is
visible in the images: the highlighted run can include running-head furniture
and footnote lines when the retrieved chunk spans them (the standing backlog item
about stripping page furniture).

## 5. Integration and dependency burden (measured, not estimated)

Added to the project `.venv` (project-local only; nothing system-wide):

- benchmark path: `rapidocr` 3.9.2, `onnxruntime` 1.30.0, `opencv-python`
  5.0.0.93, `shapely` 2.1.2, `pyclipper` 1.4.0, `omegaconf` 2.3.1,
  `antlr4-python3-runtime` 4.9.3, `colorlog` 6.12.0, `flatbuffers` 25.12.19,
  `protobuf` 7.36.2, `six` 1.17.0;
- the blocked OCRmyPDF path also installed `ocrmypdf` 17.13.0 (importable, not
  runnable here) plus `pikepdf` 10.16.0, `img2pdf` 0.6.3, `fpdf2` 2.8.9,
  `fonttools` 4.66.1, `lxml` 6.1.3, `pdfminer.six` 20260107, `pluggy` 1.6.0,
  `uharfbuzz` 0.56.2, `cryptography` 50.0.2, `cffi` 2.1.1, `pycparser` 3.0,
  `defusedxml` 0.7.1.

Code: 6 new files under `tools/` (benchmark, OCR cache + evidence source,
pipeline, probes, margin scan, demo) and 2 docs. **No existing product code was
deleted or replaced**, no default code path changed, and no existing dependency
was upgraded.

Regression status after the experiment: T003 probes **15/15**, T004 probes
**16/16**, new T006 probes **5/5**; `C04.pdf` sha256 `d3e3b068…b48c1` and the
T001 results JSON sha256 `68238b48…c335` re-verified unchanged, C04 mtime
untouched.

## 6. Recommendation

**PARTIAL_REUSE — RapidOCR as an optional, explicitly user-triggered scan
ingestion component; default text-layer path unchanged.**

Why not pure `ADOPT`: the evidence is strong but bounded (one real case, a
six-page accuracy cross-check, no certified ground truth), OCR text still needs
page-image verification before it can be cited, the page-image cache is a real
disk cost, and durable architecture adoption is explicitly a human decision under
this brief. Why not `KEEP_NO_OCR_FOR_MVP`: the engine is free, licence-clean,
needs no system binary or administrator rights, produces page-stable searchable
Chinese text, and integrates with the proven chunker, retrieval and evidence
layers with **no** changes to any of them.

OCRmyPDF remains recorded as `BLOCKED_INSTALL`; it is not rejected on merit.

## 7. Exact next action

1. User decision on durable adoption (Human Gate). The reversible work needed to
   make that decision is already done, committed and pushed.
2. If scan coverage is adopted: decide whether to keep RapidOCR (least
   infrastructure; the adapter already exists) and whether to re-attempt OCRmyPDF
   through a project-local package manager — that needs explicit approval because
   it adds a second package manager.
3. If adopted: wire the OCR path into the product entry point behind an explicit
   "source is a scan" switch, keep the page-image verification warning on every
   OCR evidence object, and settle the printed-page → PDF-page mapping policy
   (currently unresolved and never guessed).
4. Independent verification still owed: a certified human transcription of the
   frozen sample and at least one more real scan case, before any accuracy claim
   is published.

## 8. What this task does not authorize

- No durable OCR dependency and no architecture change; final adoption stays a
  human decision.
- No custom OCR model, no fine-tuning.
- No paid/API OCR, no administrator elevation, no WSL/Docker/CUDA, no system-wide
  change.
- No source-acquisition or product-UI work; the demo is explicitly an
  experimental harness (see `ops/T006_DEMO.md`).
- OCR text is never source truth: it requires page-image verification.

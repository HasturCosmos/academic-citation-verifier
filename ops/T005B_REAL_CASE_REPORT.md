# T005B — Real-case generalization report

Status: COMPLETE — **honest failure state accepted by the task's own pass condition**.
Result of the new real case: `needs_ocr` (document-level). Awaiting user review.

Task brief: `ops/T005B_REAL_CASE_GENERALIZATION.md`

## 1. Case provenance and privacy-safe identifier

| item | value |
| --- | --- |
| case id | `T005B-01` |
| secondary material | 《柏拉图为什么要驱逐诗歌？》 (supplied by the user; not used in T001-T004) |
| candidate primary source | a user-supplied local scan of 柏拉图《理想国》, 郭斌和、张竹明 译 |
| source bytes / sha256 | 14,827,873 bytes / `4d8d8c8a9c29ca24edaba68ac418aa68e9b8739e2fe47004c34b0cbea33a739b` |
| pages | 459 |
| stored where | `data/private/T005B-01/` (git-ignored; never tracked) |

The source file is a local file on the user's machine. It was copied into the
private case directory and verified byte-identical by sha256; the original file
was not modified. The machine path of the original is deliberately **not**
recorded in Git.

Edition identification (source-observed, from rendered page images):

- page 1 (cover): 汉译世界学术名著丛书 / 理想国 / 〔古希腊〕柏拉图 著;
- page 3 (colophon): 商务印书馆出版, 郭斌和 张竹明 译, 统一书号 2017·366,
  1986 年 8 月第 1 版, 1986 年 8 月北京第 1 次印刷, 字数 305 千, 印数 13,200 册,
  定价 2.85 元.

Consequently the citation shells carry publisher 商务印书馆, place 北京, year
1986. Author, title and translators came from the user; publisher/place/year came
from the scanned colophon page of this very copy. Nothing was inferred by
retrieval, and no printed page number is claimed.

## 2. Raw input type and clues used

Raw input (verbatim, not cleaned or standardized):

> 在《理想国》第十卷，苏格拉底竟扬言要将诗歌逐出城邦（605B、607B）。

Input type: a Chinese secondary-source paraphrase carrying a claimed location,
not a quotation of the primary text.

Clues carried by the input (treated as fallible):

- work: 《理想国》;
- location: 第十卷 (Book X);
- canonical references: Stephanus 605B and 607B.

The clues were preserved exactly as given and were not repaired, expanded or
silently corrected.

## 3. Source/candidate material available

- the candidate primary-source scan listed above (the only source material used);
- no second edition, no text-layer twin of the same work, no external retrieval.

## 4. Observed result and status

**Status: `needs_ocr` — the candidate document has no usable text layer at all,
so the current product path cannot retrieve, localize or display any source
passage for this case.**

Stage by stage, in the order the product actually runs:

| stage | component | observed result | cost |
| --- | --- | --- | --- |
| 1. source scan | `tools/t005b_scan_probe.py` (same PDFium text API the T003 layer uses) | **459 / 459 pages have no usable text layer**; 0 normalized characters in the whole document; 0.04 s | $0 |
| 2. retrieval ingest | PaperQA2 core API `Docs.aadd` with the pinned T001/T004 settings and an explicit citation/docname | fails closed: `ValueError: This does not look like a text document: … Pass disable_check to ignore this error.`; 0 documents, 0 indexed chunks, 0.58 s | $0, 0 model calls |
| 3. evidence localization | T003 evidence layer | **not attempted** — localization needs at least one candidate passage, and no candidate exists | $0 |

Page structure confirms the reason: every sampled page (1, 3, 10, 100, 200, 300,
400, 459) holds exactly one full-page image (≈1664×2400 TIFF/JPEG) and **no font
resources at all**. This is a pure image scan, not a PDF whose text layer is
merely broken.

The paid query stage was deliberately not run: with nothing indexed, a query
could not return any source candidate, so spending tokens would have produced no
evidence about this case. That decision is recorded in the result object rather
than hidden.

## 5. Evidence

Explicit failure evidence, all under `data/private/T005B-01/`:

- `run/text_layer_scan.json` — per-page text-layer counts for all 459 pages;
- `run/t005b_result.json` — full run record: case input, source fingerprint,
  stage results, the `needs_ocr` document object, citation shells, warnings and
  unresolved fields;
- `run/run_summary.json` — the aggregates below;
- `parse/pages/page_0001.png`, `page_0003.png`, `page_0010.png` … — rendered
  pages used only to confirm identity/edition and the image-only structure;
- no highlight image and no page-geometry record exists, because none was
  produced (no guessed geometry).

Aggregates:

```
status                          needs_ocr
pages                           459
pages_with_usable_text_layer    0
total_normalized_chars          0
model_calls                     0
cost_usd                        0.0
```

The product-level record deliberately keeps `original_text = null`: the case
input is a secondary-source paraphrase, so putting it in the source-evidence
field would misrepresent it as retrieved primary text.

## 6. Is the status honest and reproducible?

Honest: yes.

- no evidence, quotation, page number or highlight was invented;
- the product reports a source-coverage/ingest limitation instead of reporting
  "the passage was not found", which would have been a stronger and false claim;
- the T004 contract's `needs_ocr` status is used exactly as designed ("the page
  has no usable text layer; OCR is out of scope");
- the case input and the confirmed metadata are kept separate from the (absent)
  source evidence.

Reproducible: yes, at zero cost:

```
PQA_HOME=<repo> .venv/Scripts/python.exe tools/t005b_case_run.py \
  --pdf data/private/T005B-01/source/T005B-01_source.pdf \
  --case data/private/T005B-01/case/T005B-01_case.md \
  --metadata data/private/T005B-01/inputs/primary_document.json \
  --docname T005B-01 --out-dir data/private/T005B-01/run

.venv/Scripts/python.exe tools/t005b_scan_probe.py \
  --pdf data/private/T005B-01/source/T005B-01_source.pdf
```

Regression: T003 probes **15/15 PASS**, T004 probes **16/16 PASS** (both
zero-cost, re-run unchanged). `C04.pdf` sha256
`d3e3b068…b48c1` and the T001 results JSON sha256 `68238b48…c335` are unchanged,
and the C04 PDF mtime is untouched. C04 artifacts were not used as evidence for
this gate.

## 7. Runtime and cost

- model/API calls: **0**
- cost: **$0.00**
- wall clock: text-layer scan 0.04 s; PaperQA2 ingest attempt 0.58 s; total run
  ≈ 68 s including local model loading
- dependency changes: **none** (project `.venv`, `paper-qa` 2026.8.12,
  `pypdfium2` 5.13.0)
- the only network activity was the local embedding model's HuggingFace
  reachability checks, which fell back to the local cache; no API was called.

## 8. Newly exposed product gaps

1. **No scan/OCR ingestion path (confirmed).** The current stack cannot ingest an
   image-only source at all: the retrieval component refuses the file before any
   passage can be considered. For a product aimed at humanities primary sources
   — where the useful full texts are very often scans or facsimiles — this is the
   largest confirmed coverage hole found so far. T004's `needs_ocr` status was
   previously proven only by a synthetic fixture; this case proves it on real
   material end to end, at the document level.
2. **Humanities clue schemes do not fit the current hint field (confirmed).** The
   real clue in this case is a *canonical* location (Book X; Stephanus 605B/607B),
   while the pipeline's hint is a retrieval page label such as `pages 109-109`.
   There is currently no mapping between Stephanus/canonical references, the
   卷/页 of a specific Chinese translation, and PDF sequence pages. This would
   still be a gap even if the scan were OCR'd: once a document is searchable, a
   canonical clue still has to be turned into a search target.
3. **Paraphrase-to-literal-search (hypothesis, NOT tested here).** The input is a
   Chinese paraphrase written by the secondary author, so a literal
   substring search for that wording would not match a legitimate primary text.
   Because this source has no text layer, the hypothesis could not be tested in
   T005B and is recorded as untested, not as a finding.

Capability/source-coverage limitation recorded per brief item 3: the honest
classification is "current source coverage cannot read this candidate document",
**not** "the source passage does not exist" (the brief's guardrail).

## 9. Can the gap be solved by existing reusable components?

Yes, and the Reuse-first gate has already been partly triggered for exactly this
capability:

- `ops/REUSE_SCAN_2026-10-01.md` already names the relevant reusable options —
  OCRmyPDF, PaddleOCR, MinerU and Docling — and its guardrail states: *"Do not
  build custom OCR … before checking Docling/citefact/RefChecker and related
  maintained projects first."* The same scan records that
  `hearthresearch/citefact` (MIT) already converts PDFs through Docling and *can
  OCR scans*;
- `ops/T002_ARCHITECTURE_PLAN.md` already lists MinerU and OCR (PaddleOCR /
  OCRmyPDF) as deferred fallbacks to be used only when a demonstrated failure
  requires them;
- the T003 evidence layer and upstream Ethos both already model the same
  fail-closed intent (`needs_ocr` / `ocr_required`), so the evidence contract
  needs no redesign — only a new *ingestion* capability behind it.

No custom OCR code, no new dependency and no upstream modification was made in
T005B. Per the brief, the run stopped at the explicit OCR requirement.

If the project wants scan coverage, the correct next step is a bounded OCR
reuse benchmark (candidate engines, Chinese quality on this exact 459-page
facsimile, Windows-runnability, cost, and whether the resulting text is good
enough for page-accurate evidence) — a durable dependency/architecture choice,
therefore a human gate.

## 10. Pass condition

The brief passes when a genuinely new real case runs through the current product
path without invented evidence and the system either returns traceable evidence
correctly or **fails honestly with a reproducible explicit status**. This case
did the latter: `needs_ocr`, reproducible at zero cost, with no fabricated
evidence and no silent clue repair.

Gate: this result is a feasibility/coverage finding for one case. It is not a
durable architecture decision, not an OCR authorization, and not M1 acceptance.

# T006 — OCR reuse benchmark report

Status: **Phase 1 (static) COMPLETE. Phase 2 (runtime benchmark) NOT EXECUTED.**
Brief: `ops/T006_OCR_REUSE_BENCHMARK.md`.

Nothing was installed, downloaded, or executed for this report: no OCR engine,
model, Tesseract/Ghostscript, WSL/Docker/CUDA component, or other dependency.
No product code and no private source material were changed.

Date: 2026-10-01

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
| 5 | datalab-to/surya | Apache-2.0 | 21,434 | 2026-09-11 | 90+ languages | pip + torch | layout / reading order / OCR boxes | torch inference (torch already in `.venv`) |
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

- Project `.venv`: Python 3.11.9 with `torch` 2.14.1, `transformers` 5.18.0,
  `sentence-transformers` 6.1.0, `huggingface_hub` 1.33.0, `numpy` 2.4.6,
  `pypdfium2` 5.13.0, `Pillow` 12.3.0, `pypdf` 6.19.0, `litellm` 1.84.1,
  `paper-qa` 2026.8.12.
- **No OCR binary on `PATH`**: `tesseract`, `gswin64c` and `magick` are absent.

### 1.2 Corrections to earlier notes

- **MinerU is not AGPL.** Its `LICENSE.md` reads "MinerU is licensed under
  Apache License 2.0 and is subject to the additional terms below"; the added
  terms require a separate commercial licence only above 100M MAU or USD 20M
  monthly revenue, plus an attribution obligation for online-service use.
- **Marker is Apache-2.0**, verified from its `LICENSE` file.

## 2. Approved runtime candidates (shortlist of two)

The brief allows at most two runtime candidates. These two are approved for
Phase 2, and they are deliberately complementary: one preserves the existing
pipeline, one replaces its weakest likely component.

1. **OCRmyPDF** (`--language chi_sim`) — chosen because it is the only candidate
   whose output feeds the proven PaperQA2 + T003 path *unchanged*: it writes an
   invisible, bounding-box-positioned text layer into the PDF, so
   `tools/t003_evidence_localize.py` needs no new evidence code. Dependency
   burden is the reason it is a benchmark candidate rather than an automatic
   adoption: Ghostscript + Tesseract + a `chi_sim.traineddata` download.
2. **RapidOCR** (`pip install rapidocr onnxruntime`) — chosen as the
   modern-Chinese engine with the least infrastructure: Apache-2.0, CPU-only
   ONNXRuntime, no system binary, no torch. Its own README states the project
   "converted the models in PaddleOCR into the highly compatible ONNX format",
   so it carries the PP-OCR model lineage without the `paddlepaddle` runtime —
   which is why it occupies the slot the brief reserved for PaddleOCR.

### 2.1 Why the brief's other two named candidates are not shortlisted

- **PaddleOCR** — not shortlisted *separately*, because RapidOCR is the same
  model family with strictly less infrastructure. PaddleOCR becomes the named
  fallback if RapidOCR's accuracy on this facsimile proves insufficient, in
  which case the extra `paddlepaddle` runtime is justified by measured need.
- **Docling** — not shortlisted because it is an *engine host*, not an engine:
  it would add a second document representation next to the pypdfium2 layer
  (exactly the objection T005A raised against Ethos) while still delegating
  recognition to Tesseract, EasyOCR or RapidOCR. Benchmarking the engine
  directly is cheaper and removes a layer.
- **MinerU** — not shortlisted because it is heavier than this step needs
  (large model downloads, GPU-preferred) and it bundles parsing/layout work the
  T003 layer already does.

## 3. Benchmark sample

Defined for Phase 2, not yet processed:

- source: the existing private `data/private/T005B-01/` 459-page facsimile
  (unchanged, still the only real scan case);
- pages: a small fixed set — the already-rendered/identified T005B pages plus a
  few body-text pages, chosen before any engine runs so the sample is not
  tuned to a winner;
- ground truth: hand-transcribed from the page images for the sample only.
  **The secondary paraphrase must never be used as ground-truth primary text.**

## 4. Measured results

**PENDING — Phase 2.** No engine was executed under this task, so there is no
Chinese character accuracy, reading-order, runtime, or resource measurement.
This is a real gap, not an omitted detail: everything in §1 ranks *reuse cost
and license risk*, not observed accuracy on this 1986 商务印书馆 铅印 facsimile.

## 5. Integration and dependency burden (static assessment)

- OCRmyPDF: no product-code change expected on the evidence side; the new work
  is the OCR step itself plus binary provisioning. Highest setup burden, lowest
  integration burden.
- RapidOCR: no system binary, but it produces boxes rather than a PDF, so a thin
  adapter is required to map boxes into the evidence fragments that the existing
  highlight renderer already consumes. Lowest setup burden, small integration
  burden (~one file).
- Neither candidate requires deleting existing project code, and neither
  replaces PaperQA2 retrieval or the T003 localization rules.

## 6. Recommendation

**PENDING — Phase 2.** The recommendation will be one of ADOPT /
PARTIAL_REUSE / KEEP_NO_OCR_FOR_MVP, and it must be based on the measured
results in §4. Committing to one now would be exactly the premature
architecture choice the brief's guardrails forbid.

## 7. Exact next action if adoption is recommended

Phase 2, only after the user passes the human gate:

1. the user authorizes the specific installs (OCRmyPDF + Ghostscript +
   Tesseract + `chi_sim`, and/or `rapidocr` + `onnxruntime` + model weights);
2. run both engines over the fixed §3 sample;
3. record Chinese character accuracy, reading order, page provenance, whether
   retrieval/evidence stages accept the output, runtime and resource use;
4. re-run T003 15/15 and T004 16/16 regression probes and re-verify the C04
   hashes and mtime;
5. fill in §4 and §6 above and return for the adoption decision.

## 8. What this report does not authorize

- It authorizes no OCR engine, model, or system package install.
- It authorizes no durable OCR dependency and no architecture change; per the
  brief, final adoption stays a user decision.
- It authorizes no custom OCR model, no fine-tuning, no full 459-page OCR, and
  no source-acquisition or UI work.
- It does not treat OCR text as source truth: an OCR result still requires
  page-image verification before it can become evidence.

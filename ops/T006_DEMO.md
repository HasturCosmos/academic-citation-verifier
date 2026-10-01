# T006 experimental demo — launch instructions

Status: **experimental**. This is not the final product UI, not a durable OCR
adoption, and not a milestone acceptance. It exists so the overnight work is
demonstrable instead of only described.

## What it shows

Two honest stages over one real case (T005B-01, an image-only 459-page scan of
柏拉图《理想国》，郭斌和、张竹明译，商务印书馆1986):

1. **Text-layer scan** — the default product path reports `needs_ocr` and
   fabricates nothing.
2. **Experimental OCR evidence path** — RapidOCR reads the pages, retrieval runs
   over the OCR text with the pinned *local* embedding (no LLM, $0.00), and the
   unchanged T004 evidence builder returns product objects with page provenance,
   highlighted original-page images, explicit statuses and metadata-honest
   citation shells.

Every page image, OCR text and evidence object stays under `data/private/`
(git-ignored). Only code and documentation are committed.

## Prerequisites

- Project virtual environment `.venv` (Python 3.11.9).
- `rapidocr` + `onnxruntime` installed **inside** that environment
  (`pip install rapidocr onnxruntime`). The ONNX models ship inside the wheel.
- `ocrmypdf` is installed but **cannot run** in this environment: it needs
  Ghostscript and Tesseract, which are absent and only obtainable through an
  administrator-level installer. See the benchmark report for the evidence.

## One-command demo

From the repository root (PowerShell):

```powershell
$env:PQA_HOME = $PWD
$env:HF_HUB_OFFLINE = "1"
.\.venv\Scripts\python.exe tools\t006_demo.py `
  --pdf data/private/T005B-01/source/T005B-01_source.pdf `
  --ocr-cache data/private/T006-01/ocr/rapidocr `
  --out-dir data/private/T006-01/demo
```

Then open `data/private/T006-01/demo/demo_report.html` in a browser. The report
contains the run summary, the secondary-source input, every retrieved candidate,
its status, its page provenance and the highlighted original-page images.

## Component commands

```powershell
# 0) freeze the benchmark sample before running any engine (already committed as
#    the fixed page list 1, 3, 10, 30, 200, 420)
.\.venv\Scripts\python.exe tools\t006_ocr_benchmark.py `
  --pdf data/private/T005B-01/source/T005B-01_source.pdf `
  --out-dir data/private/T006-01 --freeze

# 1) benchmark RapidOCR on the frozen sample
.\.venv\Scripts\python.exe tools\t006_ocr_benchmark.py `
  --pdf data/private/T005B-01/source/T005B-01_source.pdf `
  --out-dir data/private/T006-01 --engine rapidocr

# 2) OCR the whole document into the resumable per-page cache
.\.venv\Scripts\python.exe tools\t006_ocr_evidence.py `
  --pdf data/private/T005B-01/source/T005B-01_source.pdf `
  --cache-dir data/private/T006-01/ocr/rapidocr --dpi 300

# 3) run the OCR evidence pipeline alone (writes JSON + HTML)
.\.venv\Scripts\python.exe tools\t006_ocr_pipeline.py `
  --pdf data/private/T005B-01/source/T005B-01_source.pdf `
  --ocr-cache data/private/T006-01/ocr/rapidocr `
  --out-dir data/private/T006-01/ocr_run

# 4) zero-cost regression probes for the new OCR path
.\.venv\Scripts\python.exe tools\t006_ocr_probes.py
```

## How to read the result honestly

- The OCR text is a *machine reading of an image*, not a publisher text layer.
  Every evidence object carries that warning and lists `ocr_text_verification`
  as an unresolved field.
- The printed book page is still unresolved, so no printed page number appears
  in any citation — a PDF sequence page is never substituted for it.
- Margin markers (Stephanus letters, printed page numbers, running heads) are
  recognised as their own short lines and can interrupt a passage that crosses
  them; that is a reading-order property of OCR, not a retrieval finding.
- If a page has no OCR cache entry the path reports `needs_ocr` for that page
  instead of emitting geometry.

## Known limits / not done here

- No OCR engine is bundled, auto-installed or adopted permanently.
- No full-document OCR happens automatically inside the demo; it reads the cache
  produced by step 2.
- No UI framework, branding, hosting or deployment work is included.

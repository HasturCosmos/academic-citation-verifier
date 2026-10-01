# Overnight report — 2026-10-02

Batch: `ops/OVERNIGHT_GOAL_2026-10-01.md` (authorized 2026-10-01; T006 Phase 2
human gate passed by the user).
Status: **completed at the highest honest level reached. No Human Gate was hit
during execution.**

## 1. What completed

**Stage A — T006 Phase 2 bounded OCR benchmark: COMPLETE.**

- The benchmark sample was frozen *before* any engine ran: PDF pages 1, 3, 10,
  30, 200, 420 of the T005B-01 scan at 300 dpi, with every rendered page's
  sha256 and the extracted `sample.pdf` sha256 recorded.
- **OCRmyPDF → `BLOCKED_INSTALL`.** The package installs project-locally; the
  runtime fails closed (`EXIT=3`) because Ghostscript and Tesseract are absent
  and only an administrator-level package manager is available. Recorded, not
  pursued, no elevation triggered.
- **RapidOCR → works.** 3.9.2 + onnxruntime 1.30.0, ONNX models inside the
  wheel, ≈9.5 s/page at 300 dpi on CPU. The full facsimile was OCR'd once:
  **459/459 pages, 0 pages without text, 239,966 characters, 59.3 min**.
- Accuracy was **not** turned into a fake number: no certified ground truth
  exists, so no CER is claimed. A bounded visual cross-check over the 99 body
  lines of the frozen sample found 1 genuine character substitution, 1
  punctuation substitution, a few punctuation-width differences, 2 bracket
  variants, 3 margin tokens merged into body lines, and 1 dropped character in
  a spaced running head.

**Stage B — experimental OCR integration: COMPLETE, and validated on the real
case.**

- Thin adapter: one `PdfEvidenceSource` subclass with three overridden methods.
  Chunking (`paperqa.readers.chunk_pdf`, 400/100), retrieval
  (`Docs.aadd_texts`/`retrieve_texts`, pinned local embedding) and the T004
  evidence-object builder are all reused **unchanged**. No existing code was
  deleted or replaced and no default path was changed.
- T005B-01 moved from document-level `needs_ocr` to **10/10 `located`** evidence
  objects with verified highlight geometry, at **0 model calls and $0.00**.
- The case's own region was recovered: the Book X passage on expelling poetry is
  **rank 7 → PDF pages 417–418**, the page whose right margin carries the
  verified Stephanus `607` marker. Reported honestly as **Top-1 miss,
  Top-10 hit**; retrieval was embedding-only and no reranking was tuned.

**Stage C — one-command demo: COMPLETE.**

- `tools/t006_demo.py` runs the honest two-stage story in one command — stage 1
  prints `needs_ocr` for the source, stage 2 shows the OCR evidence — and writes
  `demo_report.html` plus T004-shaped evidence objects.
- Launch command and honest-reading guidance: `ops/T006_DEMO.md`.
- Output path for the run performed overnight:
  `data/private/T006-01/demo/demo_report.html` (private, git-ignored).

**Stage D — tests, state and handoff: COMPLETE.**

- Regressions: T003 **15/15**, T004 **16/16**, new T006 probes **5/5**.
- Integrity: `C04.pdf` sha256 `d3e3b068…b48c1`, T001 results JSON sha256
  `68238b48…c335`, T005B source sha256 `4d8d8c8a…a739b` — all unchanged; C04
  mtime untouched.
- State updated: `ops/PROJECT_STATE.md`, `ops/TASK_QUEUE.md`, `ops/RUN_LOG.md`,
  `ops/AGENTS`-level current gate, and this report.

## 2. What failed or is blocked

| item | status | reason |
| --- | --- | --- |
| OCRmyPDF runtime benchmark | **BLOCKED_INSTALL** | Ghostscript + Tesseract absent; only Chocolatey (elevation) available; brief says record and continue |
| certified character-accuracy measurement | **NOT DONE (by rule)** | no independent ground truth could be produced safely; inventing CER would violate the evidence rule |
| certified human transcription | **OWED** | requires a human, not the agent |
| printed book page → PDF page mapping | **UNRESOLVED (by design)** | never guessed; no printed page appears in any citation |
| LLM rerank of the OCR candidate list | **NOT RUN** | would require a paid call, which the overnight brief gates |

No stop condition was triggered: no money was spent, no elevation was requested,
no private data left the machine, no product scope changed, no permanent
architecture choice was made.

## 3. Benchmark evidence (headline numbers)

| metric | value |
| --- | --- |
| frozen sample | PDF pages 1, 3, 10, 30, 200, 420 @ 300 dpi |
| sample output | 108 lines (99 body + 9 margin), 1,592 chars, 48.0 s, median line score 0.992 |
| full document | 459/459 pages, 0 pages without text, 239,966 chars |
| full-run wall clock | 3,557.8 s (≈59.3 min), median 8.91 s/page |
| cache on disk | 399.4 MB (git-ignored; PNG dominated) |
| model calls / cost | **0 / $0.00** for the entire task |
| real-case evidence | 10/10 `located`, highlight geometry verified visually |
| clue mapping | Stephanus `605` → PDF 415, `607` → PDF 418 (both page-image verified) |

Full detail: `ops/T006_OCR_REUSE_REPORT.md`.

## 4. Experimental demo status and launch command

Status: **working, experimental, not a product UI.** It is a local harness plus
a generated HTML evidence report; no framework, hosting, branding or
deployment work was done.

```powershell
$env:PQA_HOME = $PWD
$env:HF_HUB_OFFLINE = "1"
.\.venv\Scripts\python.exe tools\t006_demo.py `
  --pdf data/private/T005B-01/source/T005B-01_source.pdf `
  --ocr-cache data/private/T006-01/ocr/rapidocr `
  --out-dir data/private/T006-01/demo
```

Then open `data/private/T006-01/demo/demo_report.html`.

## 5. Exact commits

- `5313d91` — overnight batch authorization, synced by fast-forward (no merge
  commit created; local `main` was 11 commits behind).
- `753d315` — code checkpoint: benchmark harness, OCR evidence source, OCR
  pipeline, probes, demo, demo docs.
- `be9bf89` — Phase 2 results: this report, the filled-in
  `ops/T006_OCR_REUSE_REPORT.md`, the margin-scan tool, and the state updates
  (`PROJECT_STATE`, `TASK_QUEUE`, `RUN_LOG`, `AGENTS.md` current gate).
- The commit immediately following `be9bf89` records these exact hashes here and
  is the overnight tip.

All work is pushed to `origin/main`.

## 6. Remaining Human Gates

1. **Durable OCR adoption** — recommendation is PARTIAL_REUSE, but adoption
   itself is the user's decision.
2. **Approving a project-local package-manager route** (e.g. micromamba) if the
   blocked OCRmyPDF candidate is to be benchmarked after all; that adds a second
   package manager and is a broader change than this batch authorized.
3. **Printed-page → PDF-page mapping policy** for the product.
4. **Any accuracy claim** — requires a certified human transcription and at
   least one more real scan case.

## 7. Recommended NEXT (one)

**Decide the OCR adoption question, then, if adopted, wire the already-written
OCR path into the product entry point behind an explicit "source is a scan"
switch — keeping the page-image verification warning on every OCR evidence
object.**

Everything needed for that decision is already reversible, committed and
reproducible at $0.00. The single most valuable follow-up that is *not* blocked
by the user is a second real scan case through the same command, which would
turn "one real case" into "two real cases" and cost nothing but machine time.

## 8. Honest boundaries of this result

- This is **not** MVP completion and **not** durable architecture acceptance.
- OCR text is a machine reading of an image; it is never treated as source truth
  and every OCR evidence object says so and lists `ocr_text_verification` as
  unresolved.
- The demo shows real retrieved text only when retrieval actually returned it;
  the `needs_ocr` stage is displayed as a failure rather than papered over.
- The Stephanus margin mapping is a **measurement** with a known false-positive
  class (index pages), verified for the two case targets only.
- The known backlog item about stripping page furniture from highlights
  (running heads, page numbers, footnote lines, margin markers) is now visibly
  relevant to the OCR path and remains open.

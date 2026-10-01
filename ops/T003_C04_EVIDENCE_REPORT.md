# T003 — C04 candidate-to-highlight experiment report

Status: COMPLETE — PASS (primary route succeeded)

Brief: `ops/T003_C04_HIGHLIGHT_EXPERIMENT.md`
Contract reference: `ops/T002_ARCHITECTURE_PLAN.md` §3–§4

## 1. What was built

A thin, retrieval-independent evidence-localization layer. No retrieval code was
changed and PaperQA2 was not rerun.

| Artifact | Role |
| --- | --- |
| `tools/t003_evidence_localize.py` | candidate text + page hint -> located page(s) + character boxes -> original page render + highlighted render + JSON evidence record |
| `tools/t003_regression_probes.py` | regression probes and the synthetic (non-private) PDF fixtures they generate |

Implementation shape:

- normalization removes whitespace and invisible format characters only
  (soft hyphen, zero-width space/joiner, BOM) and keeps a mapping back to the
  original character positions; digits, annotations and CJK characters are
  never removed to force a match;
- the stored page range is used as a fallible hint: it is searched first with a
  ±1 page window, and only if that fails is the whole 1800-page document
  searched (the fallback is recorded via `hint_confirmed=false`);
- statuses are `located` (exactly one full match), `ambiguous` (many matches),
  `unmatched` (no match) and `needs_ocr` (hint page has no usable text layer);
- only `located` candidates produce geometry or images, so no guessed highlight
  is ever emitted;
- cross-page candidates produce one fragment per PDF page;
- pixel coordinates are produced by `FPDF_PageToDevice` with the same
  `start/size/rotate` arguments that `FPDF_RenderPageBitmap` receives, so crop
  and rotation are handled by PDFium itself instead of an assumed y-flip; PDF
  native character boxes, CropBox, rotation and device size are all stored;
- highlights are per-character boxes grouped into text runs (140 runs over 11
  pages), never one rectangle over unrelated body text;
- pages are rendered at 144 DPI (1224x1584 px for this 612x792 pt book).

## 2. Dependencies added

Installed into the existing project `.venv` (Python 3.11.9); nothing else was
installed, no model was downloaded.

| Package | Version | Purpose |
| --- | --- | --- |
| `pypdfium2` | 5.13.0 | page text, character boxes, page -> device transform, page rendering |
| `Pillow` | 12.3.0 | highlight overlay and PNG output |

Unchanged and still pinned: `paper-qa` 2026.8.12, `pypdf` 6.19.0.

## 3. Aggregate results

Inputs: the 10 saved T001 candidates in
`data/private/C04/results/m1e1_c04_20261001-113927.json` and the original
1800-page C04 PDF. Runtime: **5.96 s** wall clock, 31 page-window lookups plus
one whole-document occurrence count per candidate.

| Candidate | Status | PDF page(s) | Located chars | Highlight runs | Min ink ratio | Stored hint confirmed |
| --- | --- | --- | --- | --- | --- | --- |
| rank-01 | located | 126 | 367 / 367 | 16 | 0.141 | yes |
| rank-02 | located | 55 | 367 / 367 | 13 | 0.137 | yes |
| rank-03 | located | 99 | 369 / 369 | 12 | 0.121 | yes |
| rank-04 | located | 130 + 131 | 367 / 367 | 7 + 8 | 0.065 | yes |
| rank-05 (historical gold) | located | **109** | 374 / 374 | 14 | 0.139 | yes |
| rank-06 | located | 1460 | 386 / 386 | 14 | 0.085 | yes |
| rank-07 | located | 1459 | 384 / 384 | 13 | 0.134 | yes |
| rank-08 | located | 124 | 386 / 386 | 14 | 0.136 | yes |
| rank-09 | located | 124 | 380 / 380 | 14 | 0.117 | yes |
| rank-10 | located | 121 | 385 / 385 | 15 | 0.147 | yes |

- 10 / 10 candidates `located`; every candidate matched **uniquely** in the full
  1800-page document (`in_pdf = 1` occurrence) and within its stored page window.
- 0 characters without a usable box, 0 invalid boxes, 0 clipped highlight runs.
- Highlight coverage of the page never exceeded 17.4 %, and the lowest ink
  density inside a highlight run was 0.065 (a line that contains only the page
  footer, see §5). Mean ink density 0.163.
- Raw evidence records and images (private, git-ignored):
  `data/private/C04/evidence/evidence_records.json`, 11 highlighted PNGs,
  11 original-page PNGs, plus `private_candidate_texts.json`.

## 4. Acceptance criteria

| Criterion | Result |
| --- | --- |
| all 10 saved T001 candidates processed | PASS (10/10) |
| every candidate ends in an explicit status | PASS (all `located`) |
| historical gold candidate localizes to PDF page 109 | PASS (rank-05 -> page 109) |
| cross-page candidate yields correct evidence on pages 130 and 131 | PASS (2 fragments, 7 + 8 runs, both `geometry_ok`) |
| located candidates have non-empty, sane highlight geometry | PASS (11/11 fragments `geometry_ok`; render size == device size; no clipped runs) |
| readable original-page screenshots | PASS (11 highlighted + 1 original inspected) |
| no guessed highlight for ambiguous/unmatched cases | PASS (rendering only occurs for `located`; verified by probes) |
| original PDF and historical T001 artifacts unchanged | PASS (see §6) |
| model/API calls: 0, cost: 0 | PASS (0 calls, $0.00) |

Visual acceptance: **11 highlighted screenshots inspected** (one per page
fragment), plus the rank-05 original page to confirm the unmarked render. Every
highlight follows the candidate text line by line, starts and ends mid-sentence
exactly where the 400-character candidate starts and ends, covers superscript
footnote markers that belong to the span, and hides no unrelated body text.
Highlighted page furniture was observed in one case (§5).

## 5. Regression probes (15/15)

Run with `tools/t003_regression_probes.py`; fixtures are synthetic Latin-1 PDFs
generated at runtime, plus two in-memory rewrites of the stored gold candidate.

| Probe | Expected | Observed |
| --- | --- | --- |
| whitespace exact / stripped / tabs+newlines / padded | located on page 1 | 4/4 located, identical span |
| repeated text twice on one page | `ambiguous`, no highlight | `ambiguous`, 0 artifacts |
| text absent from the document | `unmatched`, no highlight | `unmatched`, 0 artifacts |
| cross-page passage | 1 fragment per page | located, pages [1, 2] |
| rotation 0 | both lines locate with highlight on glyphs | located, ink 0.235/0.237 |
| rotation 90 | as above | located, ink 0.333; the naive MediaBox y-flip would give ink 0.000 |
| rotation 180 | as above | located, ink 0.235/0.237 |
| rotation 270 | as above | located, ink 0.333 |
| CropBox smaller than MediaBox | located, highlight inside the crop | located, ink 0.229 |
| page with no text layer | `needs_ocr`, no highlight | `needs_ocr`, 0 artifacts |
| wrong stored hint (page 500 instead of 109) | whole-PDF fallback, `hint_confirmed=false` | located on 109, `hint_confirmed=false` |
| gold candidate with rewritten whitespace | located on 109, complete span | located, 374/374 characters |

Documented limitations found by the probes (not failures):

- rotated pages: PDFium returns the text of a rotated page in display order, so
  a two-line passage only matches when its lines are given in that order
  (rotation 0/180/270 returned content order, rotation 90 returned display
  order). Each line still localizes and highlights correctly, so the coordinate
  conversion is unaffected; a passage spanning reordered lines on a rotated
  page would be reported `unmatched`.
- the C04 PDF has 1800 pages with rotation 0 and MediaBox == CropBox, so neither
  limitation affects this corpus.

## 6. Integrity of existing artifacts

| File | SHA-256 | Bytes |
| --- | --- | --- |
| `data/private/C04/pqa_corpus/C04.pdf` | `d3e3b0687c70fb8db9179d40b2d666ed3536bcfa14da3602a78fdc5c791b48c1` | 18 979 855 |
| `data/private/C04/results/m1e1_c04_20261001-113927.json` | `68238b48e348b148457e59409e84a8003ff244e8b4ee2a144b4a9461e8bbc335` | 26 315 |

Both hashes were captured before the run and re-verified afterwards; the PDF
mtime is unchanged (2026-09-15 14:00:37). No retrieval artifact was rewritten.

Zero API cost: the whole experiment is local CPU only — **0 model/API calls,
$0.00**. No Docling, MinerU, OCR or other new parser was introduced.

## 7. Observations and failure classes

No failure class was hit for the primary route. Three observations are worth
carrying forward:

1. **Page furniture inside candidates.** Candidate `rank-04` spans pages 130–131
   and its stored 400-character text includes page 130's running footer line
   (the same publisher/URL line that appears on every page of this PDF), which is
   therefore highlighted. The localization is faithful; the candidate text
   itself contains page furniture that pypdf included in the page text.
2. **Whole-candidate highlighting by design.** Per the confirmed experiment
   preference, the whole 400-character candidate is highlighted, so the
   highlight extends well beyond the shortest matching sentence. Trimming to a
   semantic span is a later, on-demand capability.
3. **Cosmetic only.** On rotated pages, grouping runs in device space produces
   one highlight run per character rather than per line. The union still covers
   exactly the intended text.

Two implementation defects were found and fixed during this experiment, both
caught by the acceptance/probe checks rather than by inspection:

- line grouping measured overlap against a line's accumulated extent, so every
  row of a paragraph merged into a single block rectangle;
- the first pixel conversion used `get_size()` with a rotation swap and a manual
  y-flip, which was wrong for cropped and rotated pages; it was replaced with
  PDFium's own `FPDF_PageToDevice` using the renderer's exact arguments.

## 8. Recommendation for T004

The primary route holds for C04: retrieval candidates become page-accurate,
copyable-text-highlighted evidence with zero API cost, and the reusable failure
states (`ambiguous` / `unmatched` / `needs_ocr`) exist without guessing.

Suggested next experiment, in priority order:

1. turn the private evidence record into the user-facing evidence object
   (copyable original text, page number, citation shells) and prove the
   `located / ambiguous / unmatched / needs_ocr` states reach the product
   surface end to end;
2. test one page whose text-layer geometry is hostile (multi-column, rotated, or
   with page furniture) to see whether candidate trimming or furniture
   filtering is needed before the highlight is shown to a user;
3. only if a real page cannot be localized at all, run the smallest targeted
   Docling-provenance fallback on that single page.

Do not start Docling, MinerU or OCR pre-emptively; nothing in this experiment
justified them.

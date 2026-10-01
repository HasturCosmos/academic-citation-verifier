# T004 — end-to-end backend vertical slice report

Status: COMPLETE — PASS (12/12 acceptance criteria)

Brief: `ops/T004_END_TO_END_BACKEND_SLICE.md`
Reused components: T001/PaperQA2 core retrieval, T003 pypdfium2/Pillow evidence layer

## 1. What was built

One callable backend workflow that runs the whole chain from the real
secondary-source passage to product-facing evidence objects:

```
real secondary-source query
  -> PaperQA2 core API retrieval (Docs.aadd + Docs.aquery, pinned T001 settings)
  -> ranked candidate passages (raw chunk text + page-range label)
  -> T003 evidence localization (exact page, character boxes, highlight render)
  -> evidence objects (copyable text, PDF page, image refs, status, metadata,
     Chinese footnote + reference shells)
```

| Artifact | Role |
| --- | --- |
| `tools/t004_backend_slice.py` | the workflow (live retrieval mode, offline candidate mode, `--recheck` acceptance re-evaluation) |
| `tools/t004_regression_probes.py` | 16 zero-cost probes for the product-facing layers |

Design points (all enforced by the probes):

- the product ranking comes from the PaperQA2 **core** API (`Docs.aadd` +
  `Docs.aquery`); the CLI agent is never used;
- the retrieval page label is a fallible hint for the evidence layer (window
  search first, whole-document fallback second, `hint_confirmed` recorded);
- every candidate carries an explicit status
  (`located / ambiguous / unmatched / needs_ocr`) and stays in the result; no
  single winner is forced and no highlight is emitted without a unique match;
- bibliographic metadata comes only from a caller-supplied, human-confirmed
  record; PaperQA2's inferred docname is not used at all (the workflow passes an
  explicit docname/citation, which also removes the useless citation-inference
  LLM call that produced `Rejoice2026` in T001);
- `pdf_page_numbers` and `printed_page_numbers` are separate fields; an
  unconfirmed printed page remains unresolved and is never filled with a PDF
  page, and the citation shells are compared against shells rebuilt from the
  same metadata (probe + acceptance check);
- private source text and page images are written only below `data/private/`.

## 2. Acceptance run

Command (single entry point, live mode):

```
PQA_HOME=<repo root> .venv/Scripts/python.exe tools/t004_backend_slice.py \
  --t003-probe-summary data/private/C04/evidence/probes/t003_probe_summary.json \
  --out-dir data/private/C04/t004/run
```

Started from the **real historical T001 query** read out of the gold case at run
time (38 characters, the noisy wording with the missing "，并据"); it was not
rewritten or repaired before retrieval.

| Measurement | Value |
| --- | --- |
| parse + embed + add (1800-page PDF, `st-BAAI/bge-small-zh-v1.5`, 400/100 chunks) | 400.25 s |
| query (`Docs.aquery`, LLM evidence reranking) | 19.14 s |
| evidence localization + render (10 candidates, 144 DPI) | 9.59 s |
| model/API calls | 11 total (1 answer + 10 evidence judgements) |
| tokens | 5722 prompt / 9308 completion (`deepseek-flash`) |
| cost | **$0.0128862** |
| private output | `data/private/C04/t004/run/evidence_objects.json`, `acceptance.json`, `run_summary.json`, 11 highlight + 11 original-page PNGs |

## 3. Result

All 10 retrieval candidates were localized with unique full matches; the
historical gold passage is candidate `cand-02` at retrieval rank 2 and its
evidence resolves to **PDF page 109**.

| Candidate | Rank | Evidence score | Status | PDF page(s) | Highlights | Geometry |
| --- | --- | --- | --- | --- | --- | --- |
| cand-01 | 1 | 6 | located | 126 | 16 runs | ok |
| cand-02 (historical gold) | 2 | 10 | located | **109** | 14 runs | ok |
| cand-03 | 3 | 4 | located | 121 | 15 runs | ok |
| cand-04 | 4 | 7 | located | 99 | 12 runs | ok |
| cand-05 | 5 | 8 | located | 1460 | 14 runs | ok |
| cand-06 | 6 | 10 | located | 124 | 14 runs | ok |
| cand-07 | 7 | 10 | located | 55 | 13 runs | ok |
| cand-08 | 8 | 10 | located | 1459 | 13 runs | ok |
| cand-09 | 9 | 6 | located | 130 + 131 | 7 + 8 runs | ok |
| cand-10 | 10 | 10 | located | 124 | 14 runs | ok |

- the 10 retrieved chunks are the same page set as the T001 baseline
  (55/99/109/121/124/124/126/130-131/1459/1460), but the order differs: gold is
  rank 2 here and was rank 5 in T001. The embedding-only diagnostic stage over
  the same index (`Docs.retrieve_texts`, k=10, zero extra API cost) put the
  page-109 chunk at rank 3. LLM evidence reranking is therefore the unstable
  part of the ranking, and the rank itself should not be treated as a stable
  product signal;
- every candidate kept its raw 400-character chunk text as `original_text`
  (no model summary), and every `located` candidate produced a per-line
  highlighted page image (14 runs on the gold page, ink density 0.139+ inside
  each run, 0 clipped runs);
- bibliographic metadata is human-supplied only. Citation shells produced for
  this run (identical for every candidate, because the printed page is
  unresolved):

  - footnote: `[德]马克思·韦伯：《经济与社会（第一卷）》，阎克文译，上海：上海人民出版社，2019年。`
  - reference: `[德]马克思·韦伯.经济与社会（第一卷）[M].阎克文译.上海:上海人民出版社,2019.`

  No page segment appears in either shell; `printed_page` and
  `printed_page_numbers` are listed in `unresolved_fields` for every candidate.

## 4. Acceptance criteria

| # | Criterion | Result |
| --- | --- | --- |
| 1 | one command starts from the real secondary-source query and runs the connected loop | PASS (query 38 chars from the gold case, 10 candidates, backend `paperqa-core-aquery`) |
| 2 | retrieval returns candidates without the PaperQA2 CLI agent | PASS (`cli_agent_used=false`, core API only) |
| 3 | at least one candidate localized to exact geometry with a highlight image | PASS (10/10 located, 11 images) |
| 4 | historical gold passage surfaced and its evidence resolves to PDF page 109 | PASS (`cand-02` -> page 109; tolerance: 1 inserted character, category `Nd`) |
| 5 | multiple candidates remain in the output | PASS (10) |
| 6 | each candidate has an explicit localization status | PASS (all `located`; the other three states are covered by probes) |
| 7 | result includes copyable original text | PASS (10 x 400 characters, raw chunk text) |
| 8 | citations only from confirmed metadata, no invented fields | PASS (checked per candidate; missing fields are omitted and reported) |
| 9 | PDF pages not misrepresented as printed book pages | PASS (page-less shells byte-equal to shells rebuilt from the same metadata) |
| 10 | no private text/images committed to Git | PASS (`git ls-files data/private` empty; all refs under `data/private/`) |
| 11 | runtime, model/API calls, tokens and cost recorded | PASS (see §2) |
| 12 | existing T001/T003 regression checks still pass or are unaffected | PASS (T003 15/15 probes; T004 16/16 probes; PDF and T001 result hashes unchanged) |

`acceptance.json` in the run directory carries the machine-readable evidence for
each criterion; `--recheck <run_dir>` re-evaluates them without any model call.

## 5. Regression probes (16/16, zero cost)

`tools/t004_regression_probes.py` runs on synthetic fixtures plus in-memory
metadata and covers what T003's probes cannot:

| Probe | Expectation | Result |
| --- | --- | --- |
| statuses reach the product object | located/ambiguous/unmatched all represented | PASS |
| images only for located | ambiguous/unmatched carry no images | PASS |
| cross-page candidate | one image per PDF page | PASS (pages 1 + 2) |
| wrong stored hint | whole-document fallback, reported | PASS (`hint_confirmed=false`) |
| ambiguous/unmatched warnings | explicit warnings, no geometry | PASS |
| evidence object schema | all required product fields present | PASS |
| multiple candidates preserved | retrieval order kept | PASS |
| PDF page vs printed page | separate fields, printed page unresolved | PASS |
| citation page only when confirmed | page-less shell when unknown, page segment when given | PASS |
| unresolved fields listed | `printed_page` reported, not guessed | PASS |
| missing translator | omitted from string, listed unresolved | PASS |
| no author/title | no citation shell at all | PASS |
| needs_ocr | reaches the product object with no geometry | PASS |
| tolerance accepts inserted character | 1 inserted character tolerated, category reported | PASS |
| tolerance bounded | no match at zero tolerance, no match on unrelated text | PASS |
| tolerance false-positive guard | probe corpus text never matches the synthetic passage | PASS |

The probes deliberately use a synthetic sentence rather than the real gold
passage, so no private source text is embedded in a tracked file; the real gold
passage is read from the private case only by the acceptance run.

T003's own probes were re-run unchanged in the same session: **15/15 PASS**
(`data/private/C04/evidence/probes/t003_probe_summary.json`).

## 6. Integrity

| File | SHA-256 | State |
| --- | --- | --- |
| `data/private/C04/pqa_corpus/C04.pdf` | `d3e3b0687c70fb8db9179d40b2d666ed3536bcfa14da3602a78fdc5c791b48c1` | unchanged (mtime 2026-09-15 14:00:37 untouched) |
| `data/private/C04/results/m1e1_c04_20261001-113927.json` | `68238b48e348b148457e59409e84a8003ff244e8b4ee2a144b4a9461e8bbc335` | unchanged |

Private text, images and records stay under the git-ignored
`data/private/C04/t004/`. No Docling, MinerU, OCR or other new parser was
introduced; no retrieval architecture was changed.

## 7. Observations and open items

1. **Ranking is not yet stable.** Retrieval (embedding) returns the same 10
   chunks, but the LLM evidence-reranking stage reorders them between runs
   (T001: gold rank 5; T004: gold rank 2; embedding-only diagnostic: rank 3).
   Product behaviour should not depend on the exact rank.
2. **One candidate text includes page furniture** (`cand-09`, pages 130–131,
   the running footer line), carried over from the pypdf text layer. This was
   already known from T003 and remains a backlog item; it does not affect the
   gold evidence.
3. **Printed page is still unknown** for the C04 edition used here. The product
   deliberately emits no page number rather than substituting the PDF page. If
   the user confirms the printed page, the same pipeline will emit it.
4. **Rank/score semantics.** `retrieval_score` is PaperQA2's LLM relevance
   judgement, not source evidence; it is recorded in the object but listed as a
   warning so downstream UI cannot confuse it with evidence.
5. **Only `located` was exercised by the live C04 run.** `ambiguous`,
   `unmatched` and `needs_ocr` are verified through probes and synthetic
   fixtures, and will be exercised for real when a case with those properties
   is used.

## 8. Gate

T004 is a feasibility result for the C04 vertical slice: the chain is connected,
the gold passage reaches page-accurate highlighted evidence, and the citation
shells are metadata-honest. It is **not** a durable architecture decision and
**not** M1 milestone acceptance; both remain user decisions. Suggested next
steps are listed in `ops/TASK_QUEUE.md`.

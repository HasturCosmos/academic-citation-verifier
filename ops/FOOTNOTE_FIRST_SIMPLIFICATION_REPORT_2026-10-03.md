# REPORT — Footnote-first MVP simplification (V0.2) — 2026-10-03

Status: COMPLETE (D018 long-Goal execution).

Brief: `ops/FOOTNOTE_FIRST_SIMPLIFICATION_LONG_GOAL_2026-10-03.md`
(authorized). Product definition: `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md`;
decisions D022, D023. Reuse scan: `ops/FOOTNOTE_FIRST_REUSE_SCAN_2026-10-03.md`.

The superseded `ops/IDENTITY_RESOLUTION_V2_LONG_GOAL_2026-10-03.md` was **not**
executed.

## Outcome in one line

The normal product surface is now a three-block footnote-first workflow
(secondary quote/paraphrase → corresponding footnote/endnote → primary source),
the footnote is a first-class deterministic input, the cited work and the Chinese
containing publication are modelled separately and shown for user confirmation,
and network lookup happens only from those parsed clues.

## What changed

### New code (reversible, stdlib-only)

- `tools/footnote_parse.py` — deterministic footnote/endnote parser and identity
  model. Extracts author / title / year / cited page / translator / editor /
  publisher / volume / DOI / ISBN / container where they are actually written,
  records provenance per field, and separates `cited_work` from
  `containing_publications`. Chinese (`《…》`/`“…”`/`载·收于·见`) and Western
  (`"Title," in Container`, `Author, Title (Place: Publisher, Year), pp.`)
  styles are handled. Nothing is invented: a foreign work with no Chinese clue
  yields **no** Chinese container. `identity_is_useful` refuses to treat a bare
  page number or a lone `同上` as a search target.
- `tools/footnote_first_probes.py` — 16 zero-cost probes covering Long-Goal
  Stage 8 (see below).

### Product surface (`tools/mvp_app.py`)

- Normal page = three blocks only:
  - ① 二手文献内容（引用 / 转述，可直接粘贴或上传截图/PDF）
  - ② 对应脚注 / 尾注（粘贴或上传截图，自动 OCR）；this is the navigation input
  - ③ 一手文献：primary action **“识别来源并开始核验 →”**, plus
    **“上传一手文献 PDF，直接核验 →”** as a parallel path that skips source search
- New route `POST /identify`: parses the note and renders an **editable**
  confirmation of the cited work vs possible Chinese container, with per-field
  provenance and a copyable “查找这一版” bundle. It never calls the network.
- `POST /find` is now driven by the confirmed identity (author/title/DOI/ISBN →
  targeted query). An empty/general query box is **not** part of the normal flow;
  the legacy explicit-query box is kept only inside a collapsed developer block.
- Removed from the normal flow (moved into collapsed “开发者 / 高级选项”):
  built-in demo sources, `k`, OCR mode, local PDF path, metadata JSON path,
  provider diagnostics, and the free-standing open-full-text finder.
- Result page foregrounds exactly five things per candidate: **对应中文版原文 /
  原页高亮与页码 / 书目信息 / 一键复制引用 (复制脚注, 复制参考文献)**; the
  retrieval/debug table and the “四种结果状态” legend are collapsed.
- Honest failure states preserved: publication identified but no lawful PDF →
  “当前没有找到可直接使用的 PDF” + “查找这一版” + upload request, keeping the
  resolved identity; provider outage → bibliographic result kept, retry offered,
  no traceback.

No change to the canonical evidence pipeline, the upload path, the download
guardrails, dependencies, or the model/cost profile.

## Acceptance bar (from the brief)

| Acceptance criterion | Evidence |
| --- | --- |
| normal page reflects PRODUCT_V0_2 three-block workflow | `render_form`: ①/②/③ present; one primary action; probe `form has 3 blocks` |
| footnote/endnote is a first-class input | dedicated `footnote` field + `/identify` route + screenshot OCR |
| user need not know normalized Chinese title/author beforehand | `/identify` extracts, and the confirmation screen is editable |
| no-PDF lookup is targeted from the footnote, not whole-web | `/find` builds the query from parsed identity; probe 5, 8 |
| cited work and Chinese containing publication are distinct | `footnote_parse.build_identity`; probe 4 |
| user can upload an owned PDF with no source-search step | block ③-B `formaction='/extract'`; probe 6 (`search_all` never called) |
| output still gives text + highlighted page + page + copyable citations | result foreground headings; `mvp_probes` e2e |
| technical/demo controls are out of the normal flow | collapsed `details.dev`; finder/dev fields confined there |
| regressions remain green | see below |

## Stage 0 — Reuse First

See `ops/FOOTNOTE_FIRST_REUSE_SCAN_2026-10-03.md`. Existing retrieval/evidence/
citation/OCR/upload all reused unchanged. A bounded live check of Crossref,
Open Library and Wikidata showed **none** resolves a foreign work to its Chinese
publication/container; the chosen route is deterministic parsing + user
confirmation + the existing finder for lawful PDFs. A dedicated Chinese-catalogue
resolver remains a documented, gated gap.

## Stage 8 — probes

`tools/footnote_first_probes.py` — **16/16**, 0 model calls, $0.00:

1. pasted quote + pasted footnote → author/title/page (Western + Chinese)
2. footnote screenshot → RapidOCR → clues
3. footnote cites a standalone book
4. footnote cites an essay → container resolved separately and distinct
5. Chinese publication found but no accessible PDF → identity kept + “查找这一版” + upload
6. user already has the PDF → source search never called
7. ambiguous/partial footnote → editable candidate confirmation
8. no useful footnote → ask for a clue; not a broad search
9. provider failure → keep the bibliographic result, offer retry/upload, no traceback
10. text-layer evidence still works; image-only stays an honest failure; OCR route still present

## Tests / regressions

All offline, 0 model calls, $0.00:

| Suite | Result |
| --- | --- |
| `tools/mvp_probes.py` | 70/70 |
| `tools/t003_regression_probes.py` | 15/15 |
| `tools/t004_regression_probes.py` | 16/16 |
| `tools/t006_ocr_probes.py` | 5/5 |
| `tools/source_acquisition_probes.py` | 98/98 |
| `tools/footnote_first_probes.py` | 16/16 |

The single existing-network-call invariant is preserved: `mvp_app.py` still
contains exactly one `sa.search_all(` call, reached only through `POST /find`;
`mvp_pipeline.py` still never imports the finder.

## Human gates

None triggered. No paid service, key, account, credential, external upload of
private material, unauthorized/pirated source, login/borrowing bypass, broad
scraping, major architecture change, or product-scope change beyond PRODUCT_V0_2
occurred. UI simplification, deterministic parsing, local tests and reversible
refactors were executed autonomously per D018.

## Known gaps (honest, not hidden)

- Cross-lingual automatic resolution of an arbitrary foreign work to a specific
  Chinese edition is **not** available from the checked no-key routes; the
  confirmation screen and the upload path carry that case.
- The deterministic parser is a recall aid for common humanities citation
  shapes; unusual styles fall through to “未能识别” and are user-editable. This
  is recorded by design, not presented as full-accuracy parsing.
- The experimental finder is unchanged and still experimental; durable adoption
  remains a Human Gate.

## NEXT

Resume the guarded real pilot on the user's own literature-tracing tasks using
the footnote-first surface, and record value/failure evidence. D022/D023 remain
the active product definition; do not re-open the superseded identity-resolution
v2 Goal or add providers/credentials without pilot evidence and a Human Gate.

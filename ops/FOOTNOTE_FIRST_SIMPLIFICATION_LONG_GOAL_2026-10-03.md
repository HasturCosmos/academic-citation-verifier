# LONG GOAL — Footnote-first MVP simplification — 2026-10-03

Status: AUTHORIZED.

Authoritative product definition:
- ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md
- D022 in ops/DECISIONS.md

The superseded ops/IDENTITY_RESOLUTION_V2_LONG_GOAL_2026-10-03.md must NOT be executed.

## Mission

Simplify the product around the user's real academic-reading workflow:

secondary quotation/paraphrase
+ corresponding footnote/endnote
→ targeted bibliographic resolution
→ corresponding Chinese publication
→ obtain/upload matching PDF
→ locate Chinese primary passage
→ highlighted original page + page + one-click citation.

Do not turn the product into a general academic search engine.

## Stage 0 — Reuse First

Start from current repo capabilities.

Reuse:
- existing secondary text/PDF/image extraction;
- RapidOCR for screenshots/scans;
- current primary-PDF upload;
- source_acquisition adapters only as downstream targeted infrastructure;
- current PaperQA2/local retrieval;
- T003 page localization/highlight;
- T004 evidence/citation objects.

Then run only a bounded check for mature metadata/catalogue routes needed for **footnote-directed Chinese publication resolution**.

Do not build a broad provider ecosystem. Stop scanning when a minimal sufficient route is found.

Record:
- what existing capability already solves;
- what exact metadata gap remains;
- what source(s) are reused;
- why any new adapter/parser is necessary.

## Stage 1 — minimal normal UI

Ordinary user page must be simple.

Keep only three primary blocks:

### ① 二手文献中的引用 / 转述
- paste text;
- upload screenshot/image;
- upload relevant PDF/page if already supported.

### ② 对应脚注 / 尾注
- paste footnote/endnote text;
- upload screenshot/image;
- OCR if image;
- make clear this is the main navigation clue.

### ③ 一手文献
Two parallel user choices:
A. **让系统根据脚注识别并查找**
B. **我已有 PDF，直接上传**

Normal user should NOT see:
- built-in C04/T005B demo selector;
- k;
- OCR mode;
- local-path input;
- metadata JSON path;
- provider diagnostics;
- separate “③b” open-full-text card.

Move those to a collapsed Developer/Advanced area or dev-only mode.

Use one clear primary action such as:
**“识别来源并开始核验”**
(or equivalent wording after usability review).

## Stage 2 — footnote/endnote extraction

Treat footnote/endnote as a distinct input, not generic hints.

From footnote text/OCR, extract deterministic bibliographic clues where present:
- author;
- cited work / essay / chapter / book title;
- year;
- cited page;
- translator;
- publisher;
- volume/issue;
- DOI / ISBN;
- container title if explicitly stated.

Do not require all fields.

The user can inspect/edit extracted clues before the system uses them.

Secondary passage semantics remain available to disambiguate, but bibliographic identity search should be directed by the note.

## Stage 3 — work vs Chinese publication

Model separately:
- cited intellectual work (book / essay / article / chapter / lecture);
- Chinese title variants;
- containing Chinese publication (book / anthology / collected works / journal);
- translator;
- publisher/year/edition.

Required UX:
- show the system's candidate interpretation;
- if one cited essay can appear in a larger Chinese volume, display that container explicitly;
- multiple plausible Chinese publications can be shown;
- do not force a single winner without evidence;
- user can correct/select before PDF acquisition.

Do not invent a Chinese publication just because a foreign/original work exists.

## Stage 4 — targeted lookup only

Network search must be generated from parsed footnote identity candidates.

No empty/general search box in the normal flow.

Search questions are narrow:
1. does this identified cited work have a Chinese publication/translation?
2. what title/container/translator/edition corresponds?
3. is an accessible lawful/open/authorized PDF available for that specific publication?

Existing experimental source finder may be called only with these targeted candidates.

If no accessible lawful PDF:
- keep the resolved Chinese publication information;
- show “当前没有找到可直接使用的 PDF”;
- ask the user to upload that publication/edition.

Do not integrate Z-Library, other unauthorized/pirated repositories, or bypass access controls. Do not create credentials.

## Stage 5 — evidence retrieval

If user uploads a PDF or a targeted lawful PDF is available:
- use the existing canonical PDF pipeline unchanged;
- text layer first;
- RapidOCR fallback as already adopted;
- retrieve with secondary passage + note clues;
- localize original page;
- highlight;
- preserve honest failure states.

No new RAG/evidence stack.

## Stage 6 — result simplification

The result page should foreground exactly what the user came for:

1. **对应中文版原文**
2. **原页高亮**
3. **页码**
4. **书目信息**
5. **一键复制引用**

Citation UX should be simple and familiar:
- “复制脚注”
- “复制参考文献”

Hide raw retrieval/debug metadata by default.

If several candidates exist, show compact expandable alternatives.

## Stage 7 — remove/de-emphasize product clutter

Normal UX must no longer foreground:
- the broad experimental OA finder;
- provider names;
- technical OCR choices;
- retrieval depth k;
- demo sources;
- local path/metadata JSON;
- internal status vocabulary unless it helps the user understand failure.

Keep debugging tools available only in advanced/developer mode so regressions remain testable.

## Stage 8 — real workflow probes

Add zero-cost probes for:
1. pasted quote + pasted full footnote -> author/title/page extraction;
2. quote screenshot + footnote screenshot -> OCR -> clues;
3. footnote cites a standalone book;
4. footnote cites an essay/chapter and a container is resolved separately;
5. Chinese publication found but no accessible PDF -> upload request preserving exact publication identity;
6. user already has PDF -> skip source acquisition entirely;
7. ambiguous footnote -> editable candidate confirmation;
8. no useful footnote -> ask for more clue, do not broad-search;
9. provider/network failure -> preserve bibliographic result and offer retry/upload;
10. existing text-layer + RapidOCR evidence paths still work.

Use real public metadata only where stable and lawful; synthetic fixtures are fine for deterministic regression.

## Stage 9 — tests / docs / report

Run:
- mvp_probes
- T003
- T004
- T006
- source_acquisition_probes
- new footnote-first probes

Create:
- ops/FOOTNOTE_FIRST_REUSE_SCAN_2026-10-03.md
- ops/FOOTNOTE_FIRST_SIMPLIFICATION_REPORT_2026-10-03.md

Update:
- README
- AGENTS
- PROJECT_STATE
- TASK_QUEUE
- RUN_LOG

## Human Gates

Stop only for:
- paid service;
- API key/account/credential;
- unauthorized/pirated source integration;
- login/borrowing/paywall/DRM bypass;
- broad scraping;
- major architecture change;
- external upload of private user material;
- new product-scope change beyond PRODUCT_V0_2.

Routine UI simplification, deterministic parsing, bounded metadata adapters, local tests and reversible refactors are autonomous.

## Acceptance bar

PASS only if:
- normal page visibly reflects PRODUCT_V0_2's three-block workflow;
- footnote/endnote is a first-class input;
- user does not need to know normalized Chinese title/author beforehand;
- no-PDF lookup is targeted from the footnote, not a free-standing whole-web search;
- cited work and Chinese containing publication are distinct;
- user can upload an already-owned PDF without any source-search step;
- final output still provides primary text + highlighted page + page + copyable citations;
- technical/demo controls are out of the normal flow;
- regressions remain green.

This is a product simplification. Prefer deleting/hiding unnecessary UX over adding more surface area.

# POST-MVP LONG GOAL — bibliographic identity resolution + acquisition UX v2 — 2026-10-03

Status: **SUPERSEDED BEFORE EXECUTION by D022 / PRODUCT_V0_2_FOOTNOTE_FIRST. DO NOT EXECUTE AS WRITTEN.**

This file is retained only as historical context. The active product goal is the narrower footnote-first targeted workflow in `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md`.

## Mission

Fix the real-user workflow exposed by the 2026-10-03 pilot:

The user may notice a quotation/footnote but NOT know the exact primary-work title, author normalization, Chinese translation title, or the Chinese volume that contains the cited essay/chapter.

Therefore source acquisition must become:

secondary evidence
→ bibliographic clue extraction
→ primary-work identity candidates
→ Chinese title/edition/container candidates
→ user confirmation/edit
→ lawful/open PDF search OR user upload
→ unchanged page-grounded evidence pipeline.

Do not assume "author + book title" is known in advance.

## Stage 0 — Reuse First (bounded)

Check existing repo first, then current public/official metadata sources.

At minimum evaluate:
1. existing OpenAlex adapter/search;
2. Crossref REST bibliographic query for citation-string / article / chapter identity (public REST; no signup required);
3. Open Library Search API for work-level + edition-level metadata and language/edition relationships;
4. Wikidata entity search + structured relationships for title variants / editions / containing works where useful (use entity search for fuzzy discovery; SPARQL only after an entity is known, not as fuzzy search);
5. CALIS public union catalogue for Chinese-edition/container discovery, but only if there is a stable lawful query route suitable for light use; do not build brittle/high-volume scraping;
6. Google Books only as an optional metadata route; do not create/use a key without a new Human Gate;
7. WorldCat only as a documented candidate; do not integrate because current API access requires institutional subscription/credentials unless evidence says otherwise.

Record what each source can contribute:
- free-form citation lookup;
- work identity;
- translated title variants;
- edition/container relationships;
- Chinese bibliographic coverage;
- access/key/account constraints;
- reliability/provenance.

Prefer composition of mature metadata sources over a custom knowledge base.

## Stage 1 — normalized identity model

Create a thin internal model that separates:
- cited_work_type: book / essay / article / chapter / unknown
- author candidates
- original/work title candidates
- title variants (including Chinese variants)
- year / DOI / ISBN / other identifiers
- translator candidates
- container candidates (book/anthology/collected works/journal)
- edition/publisher/year candidates
- evidence/provenance per field
- unresolved fields

Do not merge "cited work" and "container volume" into one title.

Avoid fake confidence numbers unless they have a deterministic definition. Prefer evidence labels + reason strings.

## Stage 2 — clue extraction from the user's actual input

Reuse the existing secondary text/PDF/image extraction path.

From:
- pasted secondary passage;
- extracted footnote/citation text if supplied;
- OCR'd page image;
- free-form hints;

produce search clues automatically.

Manual author/title entry remains optional.

Use deterministic citation-pattern parsing where practical.
Do not introduce a paid LLM/API.
If a lightweight local model is proposed, first prove that existing deterministic + metadata search is insufficient and record the trade-off.

## Stage 3 — identity resolution

Implement a small resolver that can take:
- a raw footnote/citation string;
- partial title;
- partial author;
- quoted work/essay title;
- secondary text + hints;

and return multiple candidate identities with provenance.

Required behavior:
- Crossref/OpenAlex for scholarly article/chapter-like records;
- Open Library for book/work/edition relationships;
- Wikidata for structured entity/title/edition relationships where it materially helps;
- CALIS or another lawful Chinese catalogue only if Stage 0 proves a stable bounded route.

The resolver must allow:
- cited essay/chapter -> containing Chinese book/anthology candidates;
- original/foreign-language title -> Chinese title variants;
- several plausible containers/editions shown side by side.

Do not force a winner.

## Stage 4 — source-acquisition UX v2

Redesign section ③ as ONE module.

Desired visual hierarchy:

③ 一手文献来源

A. 上传一手文献 PDF（推荐）
   [choose file]

B. existing cached/demo sources (secondary/advanced)

[读取文本并确认 →]

Immediately below that button, inside the SAME section/card:

没有一手 PDF？让系统识别并查找 →
- default input comes from already-entered secondary text + hints/footnote;
- optional manual field: "你知道的作者/题名/年份/ISBN/DOI（不知道可留空）";
- do not require author/title.

Flow after click:
1. "我们从你提供的材料里识别到这些可能的一手文献"
2. show candidate cited works + possible Chinese containers/editions;
3. user can select/edit one candidate;
4. then run the existing lawful/open-PDF finder with generated query variants;
5. if no open PDF, show USER_UPLOAD_REQUIRED and keep the resolved identity so the user knows what PDF to look for/upload.

Do not leave ③b as a separate card/module.

## Stage 5 — network/provider failure UX

The real pilot returned "all providers unavailable".

Improve honesty and usefulness:
- distinguish ALL_PROVIDERS_UNAVAILABLE / RATE_LIMITED from "no bibliographic match";
- show concise per-provider reason;
- honor HTTP Retry-After for OpenAlex/other standard 429 responses when reasonable;
- provider failure must not erase identity-resolution results;
- offer "retry source search" without making the user re-enter identity clues;
- if metadata identity was resolved but acquisition providers are down, tell the user exactly what work/container to upload manually.

Do not create credentials.

## Stage 6 — benchmark real humanities shapes

At least test:
1. exact book identity known;
2. raw footnote/citation where title/author are partially known;
3. essay/chapter -> containing volume relationship;
4. original title / Chinese title variant;
5. no identity resolved;
6. identity resolved but all acquisition providers unavailable;
7. identity resolved but no lawful open PDF -> USER_UPLOAD_REQUIRED.

Include a Weber-style container case if a verifiable metadata source supports it; do not hard-code a result merely because the user mentioned an example.

## Stage 7 — regressions and report

Run all existing relevant suites:
- mvp_probes
- T003
- T004
- T006
- source_acquisition_probes
plus new identity-resolution probes.

Create:
- ops/IDENTITY_RESOLUTION_REUSE_SCAN_2026-10-03.md
- ops/IDENTITY_RESOLUTION_V2_REPORT_2026-10-03.md

Update AGENTS / PROJECT_STATE / TASK_QUEUE / RUN_LOG.

## Human Gates

Stop only for:
- paid services;
- API key/account/credential;
- login/borrowing;
- broad scraping where terms/access are unclear;
- external upload of user/private source text;
- new major architecture or persistent external database;
- product-scope change beyond D020.

Routine parsing bugs, provider failures, UI placement, local caches, tests and reversible adapters are autonomous.

## Acceptance bar

PASS only if:
- section ③ is one coherent primary-source module;
- user can start the no-PDF route without knowing author/title;
- identity candidates are derived from existing secondary text/hints and are editable;
- cited work is represented separately from possible Chinese container/edition;
- acquisition runs only after identity confirmation;
- provider outage is distinct from "not found";
- existing upload-PDF route remains intact;
- all regressions remain green.

This is a post-MVP improvement and does not reopen D019.

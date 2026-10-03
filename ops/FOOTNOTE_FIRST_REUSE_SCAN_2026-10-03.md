# REUSE SCAN — Footnote-first V0.2 simplification — 2026-10-03

Gate: the Reuse-first automatic gate, triggered by `ops/FOOTNOTE_FIRST_SIMPLIFICATION_LONG_GOAL_2026-10-03.md`.

Authoritative product definition: `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md`; D022, D023.

Scope of this scan: the footnote-first Long Goal adds a **footnote/endnote
parser**, a **cited-work vs Chinese-containing-publication model**, and a
**targeted lookup** step. This scan asks what can be reused for those three
things before writing anything new. It does **not** re-open durable adoption of
the experimental finder, does not add a provider, and does not create credentials.

## 1. Current repository capabilities (reuse first)

| Capability already in the repo | Reused for the footnote-first workflow |
| --- | --- |
| `tools/mvp_pipeline.py::run_pipeline` (text layer + RapidOCR, PaperQA2 chunking/retrieval, T004 evidence/citation objects) | unchanged canonical evidence path; the footnote is passed as the hint-assisted retrieval query |
| `tools/mvp_app.py` secondary text / PDF / image extraction and RapidOCR | block ① and block ② (footnote screenshot OCR) |
| `tools/mvp_app.py` primary-PDF upload + `resolve_run_source` | block ③-B "我已有 PDF" path, untouched |
| `tools/source_acquisition.py` (`search_all`, download guardrails, IA/OpenAlex rights guards) | downstream targeted lookup only, called from the single existing `/find` route |
| T003 page localization/highlight, T004 evidence/citation objects | result page (原文 / 原页高亮 / 页码 / 书目 / 引用) |
| `mvp_probes` synthetic-PDF/image fixtures and HTTP helpers | reused by the new `footnote_first_probes` suite |

Conclusion: nothing in the retrieval/evidence/citation layer needed to change.
The new work is input parsing, a small identity model, targeted query generation,
and UX deletion/hiding.

## 2. Native / Skills / Plugins / MCP check

- ChatGPT/Codex native capability: no native deterministic footnote-parser or
  bibliographic-identity service; nothing to reuse directly.
- Skills/Plugins/MCPs available in this workspace: none provide humanities
  footnote parsing or Chinese-catalogue resolution. The GitHub connector was
  used only for read-only reading of the project state.
- Installable skills/plugins: none that materially cover "footnote -> Chinese
  primary source".

## 3. Bounded metadata / catalogue route check (Stage 0 requirement)

The goal asks for a *bounded* check of mature metadata/catalogue routes for
**footnote-directed Chinese publication resolution** — i.e. mapping an
identified foreign work/essay to the Chinese publication/container that carries
its translation. Three no-key, free, lawful routes were checked live, read-only
(`data/private/_scratch_reuse_check*.py`, no downloads, no credentials):

Canonical motivating case (D023): Weber's essay "Objectivity in Social Science
and Social Policy" -> a Chinese publication/container.

| Route | What it can contribute | Observed result (2026-10-03) |
| --- | --- | --- |
| **Crossref REST** `query.bibliographic` | article/chapter work identity (original language) | HTTP 200; returns the **English** book-chapters only (`"『Objectivity』…"`, 2012/2016, `lang=en`). No Chinese edition/container. |
| **Open Library** `search.json` | work/edition metadata + `language` filter | HTTP 200; `language=chi` for the Weber work returned **nothing**; a plain Chinese query returned unrelated Chinese books (noise). No usable Chinese edition link. |
| **Wikidata** `wbsearchentities` + `wbgetentities` | structured entity labels/aliases (Chinese) | HTTP 200; the canonical entity for *Wirtschaft und Gesellschaft* (**Q1543828**) has **no `zh` label and no `zh` aliases**. `wbsearchentities` is entity-label search, not title-variant full text, and returned no Chinese publication. |

Result: **no no-key metadata route in the checked set resolves a foreign work to
its Chinese publication/container.** This is consistent with the already-recorded
observation (SOURCE_ACQUISITION_REUSE_SCAN) that CALIS/WorldCat/Google Books are
either not a stable lawful query route or require keys/subscriptions.

Consequences recorded:

- The product must **not** fake Chinese-title resolution. A foreign-language note
  with no Chinese clue yields a cited work and **no** containing publication
  (D022/D023), and the UI shows exactly that.
- Chinese container/译名 resolution is delivered by (a) deterministic extraction
  when the note itself names a Chinese container (`载/收于/见《…》`) and (b) a
  user-editable confirmation screen. Both are zero-cost and honest.
- Integrating a dedicated Chinese-catalogue resolver (CALIS/WorldCat/CNKI-style)
  remains a **documented gap**, deferred until a real pilot shows the
  deterministic + user-confirm route is materially insufficient, and subject to
  the normal Human Gate (lawful route, possibly credentials/paid).

## 4. Decision

| Option | Verdict |
| --- | --- |
| direct reuse of an existing Chinese-edition metadata resolver | **not available** in the checked set |
| small adaptation: deterministic parser + identity model + targeted query from the existing finder | **CHOSEN** |
| composition: keep the existing finder as downstream acquisition only | **CHOSEN** |
| from-scratch provider ecosystem / custom knowledge base | **rejected** (PRODUCT_V0_2 non-goal; guardrail) |

Gap that remains by design: cross-lingual automatic resolution of an arbitrary
foreign work to a specific Chinese edition. The product answers honestly when it
cannot, and keeps the resolved identity so the user can supply the PDF and resume.

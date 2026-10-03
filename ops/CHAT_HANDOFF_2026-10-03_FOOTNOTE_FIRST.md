# CHAT HANDOFF — 2026-10-03 — Footnote-first V0.2 acceptance

Status: current conversation should be sealed after this handoff.

## CURRENT

Project: 二流文科生的二手文献引用助手

Historical MVP milestone D019 remains accepted.

The active product definition is now:
- `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md`
- D022 — footnote-first targeted workflow
- D023 — target user is a secondary-literature reader, not a generic search-engine user

The latest Codex long Goal has finished:
- commit: `9c9290124c57a557c04f485281106c231b7b6100`
- report: `ops/FOOTNOTE_FIRST_SIMPLIFICATION_REPORT_2026-10-03.md`
- reuse scan: `ops/FOOTNOTE_FIRST_REUSE_SCAN_2026-10-03.md`

Latest delivered product surface:
1. ① secondary quotation/paraphrase
2. ② corresponding footnote/endnote
3. ③ primary source:
   - identify source and begin verification
   - or upload an already-owned PDF directly

Footnote/endnote is now a first-class bibliographic navigation input.

The normal UI hides demo sources, k, OCR controls, local paths, metadata JSON and provider diagnostics under Developer/Advanced.

The result surface foregrounds:
- corresponding Chinese primary text
- highlighted original page + page
- bibliographic metadata
- copy footnote
- copy reference-list citation

## LATEST CODE/TEST FACTS

New code:
- `tools/footnote_parse.py`
- `tools/footnote_first_probes.py`

Reported tests:
- mvp_probes 70/70
- T003 15/15
- T004 16/16
- T006 5/5
- source_acquisition_probes 98/98
- footnote_first_probes 16/16
- 0 model calls / $0.00 for these regressions

The superseded broad identity-resolution Goal:
- `ops/IDENTITY_RESOLUTION_V2_LONG_GOAL_2026-10-03.md`
was superseded before execution and must not be revived.

## CONFIRMED PRODUCT DECISIONS

- The user is already reading secondary literature; the product is not a general search engine.
- Real workflow: quote/paraphrase + footnote/endnote -> identify cited work -> identify corresponding Chinese publication/container -> obtain/upload PDF -> locate Chinese passage -> highlighted page -> Chinese citation.
- Do not assume the user already knows normalized Chinese title/author.
- Distinguish cited work/essay/chapter from the Chinese containing publication/edition.
- Uploading an already-owned PDF skips source acquisition.
- If no lawful accessible PDF exists, preserve the resolved Chinese edition/container, provide a copyable “find this edition” bibliographic bundle, and accept a locally obtained PDF without re-entry.
- Automated acquisition from unauthorized/pirated repositories is not integrated.
- Existing PDF evidence stack remains: text layer / RapidOCR -> PaperQA2/local retrieval -> T003 localization/highlight -> T004 evidence/citation.
- D018 remains active: default to one long Codex Goal per coherent reversible batch; GitHub is the state bus; user is not the message relay.
- Reuse First and context-health checks remain automatic project rules.

## KNOWN GAP

A bounded live check of Crossref / Open Library / Wikidata did not find a no-key route that reliably maps an arbitrary foreign cited work to a specific Chinese publication/container.

Current honest fallback:
- deterministic footnote parsing
- user-editable confirmation
- targeted finder
- user PDF upload

A dedicated Chinese-catalogue resolver remains gated and should only be promoted by real pilot evidence.

## REPO HYGIENE WARNING

Root `AGENTS.md` currently contains stale historical sections near the top (V0.1 / old current-batch wording) as well as the newer Footnote-first V0.2 state later in the file.

At the start of the next chat, first perform a small control-room cleanup so the latest product definition and current batch are unambiguous. Do not delete historical reports; only clean conflicting “current” instructions.

## UNIQUE NEXT

**In a fresh chat, first验收 the completed Footnote-first V0.2 Codex delivery (commit `9c929012`) and simultaneously clean stale “current” wording in `AGENTS.md`.**

After acceptance, resume one real user pilot with:
- an actual secondary quotation/paraphrase
- its actual footnote/endnote
- no pre-known Chinese source assumed

Do not start another architecture expansion before that pilot.

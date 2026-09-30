# PROJECT_STATE

Last updated: 2026-09-30

## Project

AI academic citation verification assistant.

## Current phase

M1 — evidence retrieval.

## Current status

- New clean Project created in ChatGPT.
- Project Instructions v1.1 installed.
- Migration baseline created and accepted.
- Research First completed.
- GitHub connector confirmed working.
- This repository is the shared state bus for Chat / Work / Codex.
- No product code has been written here yet.
- PaperQA2 has not yet been cloned or installed for this project.

## Confirmed M1 goal

Given:
- one real academic PDF;
- one real secondary-source quotation/paraphrase;

return:
- top candidate original passages;
- raw source text (not only model summaries);
- PDF page provenance;
- enough surrounding context for human verification.

## First baseline experiment

M1-E1 uses historical case C04.

Known gold facts:
- source work: Max Weber, *Economy and Society* Chinese translation by Yan Kewen, Shanghai People's Publishing House, 2019;
- historical test PDF: combined two-volume PDF, 1800 PDF pages;
- query contains a small omission/noise;
- gold original passage is on PDF page 109 (1-based);
- gold text contains the phrase equivalent to “他人的表现，并据此作为行动进程的取向”.

The C04 PDF and gold-case artifact are now ready in local private data (`data/private/C04/`), verified: 1800 PDF pages total and page 109 readable.

## M1-E1 minimum success conditions

1. Gold passage appears in Top-5.
2. Correct PDF page can be preserved/recovered.
3. Raw original text can be surfaced.
4. Sufficient local context can be recovered.
5. Record Top-1/Top-3/Top-5 rank.
6. Record integration/code modification amount.
7. Record actual API/model cost where measurable.

## Candidate technical routes

Primary baseline:
- PaperQA2-first.

Fallback only if evidence justifies it:
- MinerU 4 + existing hybrid retrieval;
- Docling / PaddleOCR / Marker as parsing fallbacks where appropriate.

## Known boundaries

Not in current scope:
- PMS;
- automatic whole-web literature discovery;
- automatic literature review writing;
- automatic paper writing;
- unnecessary multi-agent systems;
- broad production UI.

## Context health

GREEN for repository state.

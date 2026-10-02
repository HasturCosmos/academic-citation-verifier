# POST-MVP PATCH GOAL — primary-source intake — 2026-10-02

Status: AUTHORIZED LOW-RISK POST-MVP PATCH.

Read first:
- AGENTS.md
- ops/PROJECT_STATE.md
- ops/TASK_QUEUE.md
- ops/DECISIONS.md
- ops/PILOT_FINDING_2026-10-02_PRIMARY_SOURCE_INTAKE.md

## Goal

Fix the first real-user pilot blocker without reopening MVP architecture.

### Required

1. Fix blank metadata handling:
   - blank/whitespace metadata input means no metadata;
   - never resolve blank metadata to repo root;
   - only read metadata when the target exists AND is a regular file;
   - show a friendly user-facing validation error instead of a traceback.

2. Make primary-source **PDF upload** first-class in the web UI:
   - user can upload the primary PDF directly;
   - store it only under git-ignored data/private/;
   - route text-native PDF through the existing path;
   - route image-only PDF through D017 RapidOCR behavior according to the existing OCR mode;
   - preserve registered C04/T005B sources as demo/local cached examples;
   - keep manual local path as an advanced fallback, not the main UX.

3. Validate primary-source formats before starting a job:
   - PDF supported;
   - EPUB and other unsupported formats must stop early with a clear Chinese explanation;
   - explain that EPUB lacks stable page provenance/original-page evidence for this product's evidence contract;
   - do not silently convert EPUB into fake page numbers.

4. Add regression probes for:
   - blank metadata;
   - directory passed as metadata path;
   - uploaded primary PDF;
   - unsupported EPUB;
   - existing registered source behavior.

5. Run existing MVP/T003/T004/T006 regression suites and keep them green.

6. Update README and state docs. Record this as a post-MVP pilot patch, not a new MVP milestone.

## Do NOT implement in this Goal

- Z-Library or any unauthorized/pirated download integration;
- general web/source acquisition;
- paid services;
- deployment/accounts;
- EPUB-as-final-evidence conversion;
- architecture changes.

## Reuse First

Before adding upload/parsing machinery, reuse the existing HTTP multipart parser and existing private upload/run directories where possible. Do not add a framework unless current code cannot safely handle the required upload.

## Autonomy

This is a D018 Long Goal. Handle ordinary bugs/tests/refactors autonomously. Stop only at a real Human Gate or evidence-integrity blocker.

At end:
- push origin/main;
- leave tree clean;
- update PROJECT_STATE / TASK_QUEUE / RUN_LOG / AGENTS as needed;
- write one concise patch report with exact commit and launch/test commands.

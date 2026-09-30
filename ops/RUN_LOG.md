# RUN_LOG

## 2026-09-30 — Repository control plane initialized

Actor: ChatGPT via GitHub connector

Actions:
- created AGENTS.md;
- created PROJECT_STATE.md;
- created TASK_QUEUE.md;
- created DECISIONS.md;
- created RUN_LOG.md.

Purpose:
establish GitHub as the shared state bus for Chat / Work / Codex and reduce manual copy-paste handoffs.

No product code, dependency installation, PaperQA2 clone, or Codex execution was performed.

Next active task:
T001 — prepare and execute the M1-E1 PaperQA2 baseline after the C04 PDF/gold case are available to the runtime and the live Codex configuration is inspected.

## 2026-09-30 — C04 local test material acceptance

Actor: Codex (local)

Actions:
- verified `data/private/C04/` contains the C04 combined two-volume PDF and `M1-E1_C04_gold_case.md`;
- confirmed the PDF is readable with 1800 pages and page 109 extracts successfully;
- confirmed the gold-case file includes the raw query, gold original text, gold PDF page 109, and the M1-E1 minimum success conditions;
- confirmed `data/private/` remains Git-ignored and neither test file is tracked.

No PaperQA2 clone, dependency install, model call, or product-code change was performed.

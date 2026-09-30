# TASK_QUEUE

## ACTIVE — T001

### M1-E1 PaperQA2 baseline preparation

Goal:
run one real gold-case baseline with the smallest possible setup and without prematurely modifying PaperQA2 core.

Before execution:
- C04 source PDF accessible to the coding/runtime environment: DONE;
- C04 gold-case definition accessible: DONE;
- live Codex model/provider/reasoning configuration inspected and verified: DONE;
- verify the current PaperQA2 setup path from upstream docs/repo: DONE — installed upstream-style as `pip install "paper-qa>=5"` into a project-local `.venv` (Python 3.11.9, `paper-qa` 2026.8.12); no source clone, no source modification;
- run-environment smoke test: DONE — `import paperqa` OK, `pqa --help` OK (exit 0), C04 PDF readable (1800 pages, page 109 text and gold phrase present);
- DeepSeek configurability, read-only: DONE — `deepseek/deepseek-chat` is a native LiteLLM provider keyed on `DEEPSEEK_API_KEY` and supports function calling;
- choose the lowest sufficient mode for the next execution step: STILL PENDING (blocked on the items below).

Remaining prerequisites for the first real baseline run (deliberately not done tonight):
- decide the embedding path (local `st-<model>` via the `local` extra incl. model download, or `sparse`);
- pin a settings file that disables OpenAI-dependent defaults (`parsing.multimodal`, `enrichment_llm`, `use_doc_details`) and narrows `paper_directory` to `data/private/C04`;
- provide a writable PQA home (`PQA_HOME=<repo>` → repo-local `.pqa/`) and make `DEEPSEEK_API_KEY` available to the running process;
- user authorization for the baseline model spend and its cap.

Baseline must record:
- whether gold enters Top-5;
- first-hit rank;
- whether raw text is available;
- PDF page provenance;
- surrounding context availability;
- code/config changes required;
- model/API cost.

Constraint:
first run should stay as close to upstream/default PaperQA2 behavior as practical.

## NEXT

T002 — Decide whether PaperQA2 is sufficient for M1 based on T001 evidence.

Possible outcomes:
- continue with a thin adapter;
- replace only a weak parsing/retrieval component;
- escalate to MinerU-based route.

## BLOCKERS

None at the local test-material / Codex-configuration layer.

Resolved on 2026-09-30:
- upstream PaperQA2 install/run path confirmed and exercised (`paper-qa` 2026.8.12 in project `.venv`);
- network access for dependency installation was authorized and used for that install;
- setup work was done at the project's medium reasoning effort, without multi-agent or Goal modes.

Execution prerequisites still pending:
- choose the embedding model (local sentence-transformer vs. `sparse`), which is the only remaining component that needs an extra install/download;
- choose the minimal model/embedding configuration and spending cap for the baseline, then get user authorization before the first paid call.

## BACKLOG

- M2 end-to-end MVP.
- M3 real-case evaluation set expansion.
- Additional C01-C05 regression cases.
- PMS project (explicitly deferred).

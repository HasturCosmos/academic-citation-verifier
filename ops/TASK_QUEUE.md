# TASK_QUEUE

## ACTIVE — T001

### M1-E1 PaperQA2 baseline preparation

Goal:
run one real gold-case baseline with the smallest possible setup and without prematurely modifying PaperQA2 core.

Before execution:
- ensure the C04 source PDF is accessible to the coding/runtime environment;
- ensure the C04 gold-case definition is accessible;
- inspect actual Codex model/provider/reasoning configuration;
- choose the lowest sufficient mode;
- verify the current PaperQA2 setup path from upstream docs/repo.

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

- No live Codex configuration inspection has yet been recorded for T001.

## BACKLOG

- M2 end-to-end MVP.
- M3 real-case evaluation set expansion.
- Additional C01-C05 regression cases.
- PMS project (explicitly deferred).

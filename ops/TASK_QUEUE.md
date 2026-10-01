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
- choose the lowest sufficient mode for the next execution step: DONE — chunking 1200/200 and the DeepSeek LLM roles pinned in the tracked `.pqa/settings/m1e1_c04.json`; embedding is the user-approved local SentenceTransformer (`sparse` was used only for the zero-API pre-check);
- corpus isolation and run mechanics: DONE — hardlinked corpus at `data/private/C04/pqa_corpus/C04.pdf` (gold case cannot be indexed), repo-local `PQA_HOME`, tracked settings file, sandbox egress limitation identified;
- zero-API parsing and recall pre-check: DONE — clean 1800-page pypdf parse, page-range chunk provenance, and the gold chunk ranked 4th by `retrieve_texts` with `sparse` (see PROJECT_STATE "M1-E1 parsing/retrieval evidence").

Remaining prerequisites for the first real baseline run:
- embedding choice APPROVED for T001: use a local SentenceTransformer rather than `sparse`; upstream PaperQA2 tests explicitly note that `embedding="sparse"` was too weak for a retrieval test. For C04's Chinese text, use `st-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (50-language SentenceTransformer; requires the `paper-qa[local]` install/model download);
- before the paid call, locally verify which current DeepSeek model name is accepted by the installed LiteLLM 1.84.1: DeepSeek's current official API uses `deepseek-flash`, while the earlier read-only inspection recorded `deepseek/deepseek-chat`;
- settings file that disables OpenAI-dependent defaults and narrows the paper directory: DONE (`.pqa/settings/m1e1_c04.json`, corpus isolated at `data/private/C04/pqa_corpus/`);
- writable PQA home and key injection path: DONE as a mechanism (`PQA_HOME=<repo>` → repo-local `.pqa/`; key comes from the session env or a git-ignored `.env`);
- user authorization for the baseline model spend: GRANTED on 2026-10-01 with no hard cap;
- still to do: swap the pinned embedding to the approved SentenceTransformer, run the paid C04 baseline once, and record actual spend.

Known risk to watch at run time:
- the agent's file-level `paper_search` layer uses a tantivy tokenizer that handles unmarked Chinese poorly; if the agent cannot locate any paper, retry with `agent.agent_type = "fake"` or a tightened tool set rather than changing retrieval code;
- escalation is required for the run itself because the sandbox has no network egress.

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
- swap the tracked `embedding: sparse` to the already-authorized local multilingual SentenceTransformer and install/download it if not already present;
- perform the no-cost local model-name compatibility check for the installed LiteLLM 1.84.1 against DeepSeek's current API naming;
- rerun with network escalation/unsandboxed execution because the managed sandbox has no egress;
- run exactly one formal paid C04 baseline and record rank/provenance/context/cost. User authorized DeepSeek spend for this first experiment without a hard RMB cap; cost discipline still applies.

## BACKLOG

- M2 end-to-end MVP.
- M3 real-case evaluation set expansion.
- Additional C01-C05 regression cases.
- PMS project (explicitly deferred).

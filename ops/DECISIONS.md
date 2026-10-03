# DECISIONS

## D001 — Product before curriculum

Status: confirmed

Learning is just-in-time and serves the current development obstacle.
Do not restore the old generic AI-learning curriculum.

## D002 — V1 scope is intentionally narrow

Status: superseded by D010 on 2026-10-01

V1 starts from:
secondary quotation/paraphrase + candidate primary PDF.

It does not start from whole-web source discovery.

## D003 — Evidence traceability is mandatory

Status: confirmed

The product must prioritize raw source evidence, page provenance, context, and human review.
Generated summaries alone are not sufficient evidence.

## D004 — Research First

Status: confirmed

Before reinventing reusable functionality, quickly evaluate maintained open-source alternatives.

## D005 — M1 will not start from a hand-built RAG stack

Status: confirmed

Research First found mature components for parsing, retrieval, reranking, and provenance.

## D006 — Experiment PaperQA2 first

Status: confirmed

PaperQA2 is the first M1 baseline because it minimizes custom engineering.
MinerU-based architecture is a fallback, not a parallel first experiment.

## D007 — GitHub is the shared state bus

Status: confirmed

Chat / Work / Codex should synchronize through repository state instead of requiring the user to manually copy large prompts/results between surfaces.

## D008 — Cost discipline

Status: confirmed

Use the lowest sufficient model/reasoning mode and avoid Goal / Ultra / multi-agent usage unless the expected benefit clearly justifies the extra quota/token cost.

## D009 — Human gate remains for key decisions

Status: confirmed

Automation may handle low-risk execution and bookkeeping, but the user confirms product-scope changes, durable architecture choices, and milestone acceptance.


## D010 — Product definition V0.1

Status: confirmed

The user confirmed `ops/PRODUCT_V0_1.md` on 2026-10-01.

Key durable points:
- product name: 二流文科生的二手文献;
- input may be pasted text, PDF, or image/photo, plus an optional free-form hints field;
- footnotes and user hints are fallible clues, not authoritative facts;
- scope is author-agnostic; coverage is determined by currently accessible full-text sources;
- core delivery is Chinese primary-source evidence: original text + original-page screenshot/highlight + page + basic copyable citation;
- multiple plausible passages and multiple Chinese editions are shown rather than forced into a single winner;
- results use progressive disclosure;
- MVP does not need universal source acquisition before the first runnable demo;
- long interpretive verification is deferred/on-demand to control cost.

This decision supersedes the earlier candidate-primary-PDF-only product scope in D002 while preserving that workflow as a useful retrieval subproblem and evaluation route.


## D011 — T003 milestone accepted

Status: confirmed

On 2026-10-01 the user explicitly accepted T003.

Accepted evidence:
- the lightweight pypdfium2/Pillow evidence-localization route works on the C04 text-native PDF case;
- 10/10 saved candidates localized, gold on PDF page 109, cross-page evidence on 130/131, 15/15 regression probes passed;
- the evidence layer can remain separate from retrieval and emit explicit failure states without guessing.

Boundary:
this acceptance validates T003 and authorizes reuse of this route for the next reversible vertical-slice task. It does not yet finalize the entire product architecture, prove OCR/scanned-document coverage, or accept the full MVP.


## D012 — T004 milestone accepted

Status: confirmed

On 2026-10-01 the user explicitly accepted T004.

Accepted evidence:
- the first backend vertical slice starts from the real secondary-source query and reaches multiple candidate primary passages, exact PDF-page geometry, highlighted original-page images, copyable original text, and metadata-honest basic citation output;
- all 12 T004 acceptance criteria passed;
- T004 regression probes passed 16/16 and T003 regression probes passed 15/15;
- the historical gold passage surfaced and resolved to PDF page 109;
- the workflow preserves multiple candidates and does not substitute PDF sequence pages for unknown printed book pages.

Boundary:
this acceptance validates the C04 end-to-end backend slice. It does not yet establish cross-document generalization, OCR/scanned-document coverage, external source acquisition, final ranking behavior, final architecture, or full MVP acceptance.

## D013 — Product naming updated

Status: confirmed

On 2026-10-01 the user explicitly set the final product name to **二流文科生的二手文献引用助手**.

This naming decision supersedes the shorter name recorded in D010. Product scope and requirements are otherwise unchanged.


## D014 — Reuse-first automatic gate

Status: confirmed

On 2026-10-01 the user requested that avoidance of unnecessary reinvention become an automatic project-level behavior, analogous to context-health checks, rather than something that depends on manual reminders.

The repository root `AGENTS.md` now defines a mandatory Reuse-first gate for non-trivial reusable subsystems and technical-route expansions. The gate checks existing project capability, native tools, Skills/Plugins/MCPs, maintained GitHub projects, official practices, and only then custom implementation. It must stay bounded and is skipped for trivial local implementation details.

This rule is operational guidance, not permission to change durable architecture without the normal human gate.


## D015 — Batch autonomous execution for reversible work

Status: confirmed

On 2026-10-01 the user explicitly requested fewer manual ChatGPT↔Codex handoffs and preferred that Codex run multiple clear, low-risk, reversible sub-gates in one longer Goal whenever practical.

Default behavior:
- once goal, ordering, acceptance evidence and stop conditions are explicit, batch adjacent reversible tasks instead of asking the user to relay every checkpoint;
- GitHub remains the state bus and each major checkpoint is committed/pushed;
- ordinary bugs, test failures, dependency conflicts and reversible implementation choices are handled autonomously;
- stop only at the existing Human Gates (money/credentials, irreversible or broad system changes, core product-scope changes, durable architecture adoption, final brand/visual direction, unresolved value decisions).

This decision does not authorize background execution from ChatGPT when no Codex/Work control connector exists. The user may still need to start the Codex Goal once; after that, the Goal should continue autonomously within these bounds.

## D016 — T006 Phase 2 authorized

Status: confirmed

On 2026-10-01 the user explicitly approved T006 Phase 2.

Authorized scope: bounded runtime benchmarking of the Phase-1 OCR shortlist on a fixed small sample, including project-local dependencies and free model/data downloads needed for the benchmark.

Still gated: paid/API OCR, administrator/elevation prompts, WSL/Docker/CUDA installation, broad system-wide changes, and permanent OCR architecture adoption.

The authorized batch execution brief is `ops/OVERNIGHT_GOAL_2026-10-01.md`.


## D017 — RapidOCR optional scan ingestion adopted for MVP

Status: confirmed

On 2026-10-02 the user explicitly approved **RapidOCR as the MVP's optional scan-ingestion component**, while keeping the existing text-layer PDF path as the default.

Durable product/architecture meaning:
- text-native PDFs continue through the existing PaperQA2 + T003/T004 path by default;
- image-only/scanned source PDFs may invoke RapidOCR as an explicit fallback/optional branch;
- OCR output is never treated as publisher text truth and must retain the page-image verification warning;
- OCR evidence must preserve the same provenance/status/honesty contract as the text-layer path;
- OCRmyPDF remains blocked/backlog and is not part of the MVP route unless later evidence justifies its broader system dependencies;
- no paid/API OCR is introduced by this decision.

This decision promotes the T006 RapidOCR experiment from reversible evidence to an approved MVP component. It does not accept the full MVP, settle printed-page mapping policy, or authorize final brand/visual direction.


## D018 — Long Goal by default; user is not the agent message bus

Status: confirmed

On 2026-10-02 the user explicitly confirmed a project-wide operating preference for the period before ChatGPT can directly control/communicate with the local Codex runtime.

Default interaction protocol:
- before dispatching Codex, ChatGPT should package the largest coherent unit of low-risk, reversible, testable work into **one long Goal** with explicit acceptance criteria and stop conditions;
- once the Goal starts, Codex should continue through adjacent implementation → test → fix → regression → documentation → state-update checkpoints without asking the user to relay routine intermediate results;
- ordinary bugs, local dependency conflicts, reversible refactors, test failures, and implementation details are handled autonomously;
- Codex stops only at a genuine Human Gate, a repeated evidence-integrity blocker, or the final reviewable deliverable;
- GitHub is the shared state bus: Codex commits/pushes meaningful checkpoints; ChatGPT later reads GitHub directly for review instead of asking the user to paste logs/reports;
- the user should normally perform only the minimum bridge action that tools cannot automate: **start the long Codex Goal once**, then return only when a Human Gate or final acceptance is reached;
- if/when a direct ChatGPT↔Codex control/communication connector becomes available, replace this manual start/return bridge with the direct connection rather than preserving unnecessary copy/paste.

This rule sits alongside the automatic context-health check and Reuse-first gate. It does not override Human Gates or authorize background execution that the available tools cannot actually perform.


## D019 — MVP milestone accepted

Status: confirmed

On 2026-10-02 the user explicitly accepted the MVP milestone for **二流文科生的二手文献引用助手** after ChatGPT control-room review passed the delivered MVP candidate.

The accepted MVP includes:
- one canonical local product entry point (`tools/mvp_app.py`);
- shared backend contract (`tools/mvp_pipeline.py`);
- pasted text / uploaded secondary PDF / uploaded image input handling;
- optional fallible hints;
- text-native primary-source route plus D017 RapidOCR scan fallback;
- copyable Chinese source text, original-page highlight, PDF page provenance, known metadata and basic citation output;
- explicit uncertainty/failure states;
- real C04 and T005B-01 success routes plus a real insufficient-source failure route;
- zero-paid-call default retrieval path.

The user also explicitly deferred the following to **post-MVP backlog**:
1. paid LLM reranking inside the product entry point;
2. certified human OCR-accuracy verification;
3. printed-page mapping policy/implementation;
4. same-query multi-edition / multi-translation comparison.

Other already-recorded post-MVP gaps (fresh-install verification, robust multi-item detection, first-run performance, ranking stability, highlight page-furniture cleanup) remain backlog unless promoted later.

This decision closes the MVP build milestone. Do not reopen deferred items as blockers to MVP acceptance.


## D020 — Primary-source intake policy (post-MVP patch)

Status: confirmed

On 2026-10-02 the user authorized the post-MVP patch
`ops/POST_MVP_PRIMARY_SOURCE_PATCH_GOAL_2026-10-02.md` after the first real pilot
run; that authorization confirms the following product-input policy.

Durable meaning:
- the searchable primary source must be a **PDF** (text layer, or an image-only scan
  handled by the adopted D017 RapidOCR branch), because the evidence contract needs a
  stable page geometry plus an original-page image;
- EPUB and other flowable e-book formats are rejected **before** a job starts, with an
  explanation that they cannot provide page-grounded evidence; page numbers are never
  fabricated, and EPUB-to-PDF conversion is not accepted as evidence;
- blank/whitespace metadata means "no metadata supplied"; a metadata path is read only
  when it exists and is a regular file, and user-facing validation problems are shown
  as Chinese messages rather than tracebacks;
- uploading a primary-source PDF is the normal web path; uploaded files stay under the
  git-ignored `data/private/mvp_uploads/`, and registered sources remain labelled
  built-in demo/cached examples rather than the primary UX.

Boundary: this does not authorize automatic source acquisition, does not admit
unauthorized/pirated repositories, and does not reopen the accepted MVP milestone.
Lawful/open/authorized acquisition when the user has no PDF remains a separate
Reuse-First + Human Gate.


## D021 — Open-access eligibility needs an explicit rights/access signal

Status: confirmed

Recorded on 2026-10-03 from the Phase-1 control-room hardening requirement
(`ops/RUN_LOG.md` 2026-10-03; executed under
`ops/SOURCE_ACQUISITION_GUARDRAIL_PATCH_GOAL_2026-10-03.md`).

Durable meaning, for the experimental finder and for any future provider
adapter:

- a record may be auto-downloaded only when an **explicit** rights / licence /
  access signal supports it;
- broad collection membership (Internet Archive `americana`, `opensource`)
  and a work-level open-access flag are **not** sufficient on their own; only
  Project Gutenberg is trusted on collection membership alone, and an OpenAlex
  PDF must sit on a location that is itself marked open access;
- a provider's `pdf_url` is a claim, never a guarantee — the `%PDF` header
  check and the git-ignored destination stay mandatory.

Boundary: this is a guardrail on an experimental, reversible capability. It is
not durable adoption of the finder and does not reopen the accepted MVP
milestone (D019). Durable adoption stays a Human Gate; the primary-PDF upload
route remains primary.

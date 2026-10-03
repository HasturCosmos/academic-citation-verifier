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


## D020 — Primary-source identity resolution before acquisition

Status: confirmed

On 2026-10-03 the user clarified the real humanities workflow after a failed pilot.

The product must NOT assume the user already knows the exact Chinese author/title of the primary source.

Confirmed product behavior:
- the primary-source section is one unified module; "upload PDF" and "I do not have a PDF — identify/find it for me" are parallel paths inside section ③, not two visually separate product modules;
- the no-PDF path should appear immediately under the normal "读取文本并确认" action in section ③;
- manual title/author input is optional correction, not a prerequisite;
- the system should first extract/resolve bibliographic identity from the secondary passage, footnote/citation text, page image/OCR, and any user hints;
- identity resolution must distinguish the cited intellectual work (book / essay / chapter / article) from the Chinese publication container/edition in which that work may actually appear;
- one original work may map to several Chinese titles, translations, collected volumes, anthologies or editions; show plausible mappings with provenance and do not force a single answer without evidence;
- only after identity/container candidates are resolved should the lawful/open-PDF finder run query variants against available source adapters;
- if identity cannot be resolved confidently, ask the user to confirm/edit candidate metadata rather than requiring them to invent a title;
- source acquisition failure caused by provider outage/rate-limit must be distinguished from "no matching source exists".

Example motivating case:
Weber's essay "Objectivity" may be cited under an essay title in secondary literature while a Chinese translation can be contained inside a larger Chinese volume rather than a stand-alone publication. The product must model "work -> translation/title variant -> containing publication/edition" instead of assuming one cited title equals one book PDF.

This decision refines the accepted product workflow and does not reopen D019 MVP completion.


## D022 — Footnote-first targeted workflow supersedes broad finder UX

Status: confirmed

On 2026-10-03 the user refined the product from real academic-reading experience.

Current product definition: `ops/PRODUCT_V0_2_FOOTNOTE_FIRST.md`.

Durable direction:
- primary user action begins from a secondary quotation/paraphrase **plus its footnote/endnote**;
- footnote/endnote is the principal bibliographic navigation clue;
- the system performs targeted bibliographic resolution first, not general whole-web discovery;
- it must distinguish the cited work/essay/chapter from the Chinese containing publication/edition;
- only after that identity is resolved should the system check for a matching Chinese publication/PDF;
- if the user already has the PDF, upload it directly;
- if no accessible lawful PDF is available, tell the user exactly which Chinese publication/edition was identified and ask for upload;
- output remains: Chinese primary text + highlighted original page + page provenance + one-click citation formats;
- normal UI is intentionally minimal; k/OCR/debug/local-path/demo-source/provider controls move to advanced/developer mode.

The previously authorized `ops/IDENTITY_RESOLUTION_V2_LONG_GOAL_2026-10-03.md` is **SUPERSEDED before execution**. Its broad multi-provider identity-search direction must not be executed as written.

The experimental open-source finder remains reusable infrastructure but is no longer a top-level user workflow. It may be called only after footnote-guided identity resolution produces a concrete source target.

Automated acquisition from unauthorized/pirated repositories is not part of the product; access-controlled/paywalled/borrowed content is not bypassed.

D019 historical MVP acceptance remains intact; V0.2 is a product simplification/refinement driven by real pilot use.


## D023 — Target user is a secondary-literature reader, not a search-engine user

Status: confirmed

On 2026-10-03 the user refined the target persona from actual humanities study experience.

The target user is a "二流文科生" in the product's self-deprecating framing:
- they do read secondary literature;
- they can recognize that a quotation/footnote is useful;
- they usually know enough to paste/screenshot the relevant passage and note;
- they may have weak foreign-language ability and may not be able to verify or responsibly cite the foreign-language primary source directly;
- copying the secondary author's foreign-language footnote straight into their own Chinese paper creates an authenticity/verification problem and often does not match Chinese academic citation conventions.

Therefore the product's core value is not general search. It is:

**secondary quotation/paraphrase + footnote/endnote -> verified Chinese primary-source evidence -> Chinese citation ready to use.**

The product should help the user:
1. identify what primary work the note actually refers to;
2. locate the corresponding Chinese publication/container/edition;
3. obtain or accept a matching PDF;
4. verify the Chinese passage against the original page;
5. copy a Chinese footnote/reference-list citation without pretending the user personally consulted a foreign edition they did not verify.

Normal UX should minimize technical controls and general-search concepts.

Source-acquisition boundary remains unchanged:
- the product may automatically use lawful/open/authorized full text;
- it must not automate downloading copyrighted works from unauthorized/pirated repositories or bypass access controls;
- when no accessible lawful PDF is available, show the exact identified Chinese edition/container and provide a one-click copyable "find this edition" bibliographic bundle, then accept the user's locally obtained PDF and resume automatically.

This refines D022 / PRODUCT_V0_2 and does not reopen the historical MVP milestone.


## D024 — Verification exists to stop citation-error propagation

Status: confirmed

On 2026-10-03, during the first real-user pilot, the user clarified the product's
normative core after discovering that a real secondary-literature citation may
contain a propagated bibliographic/page error.

Durable direction:
- academic status, reputation, or repeated reuse does not turn a citation into
  verified evidence; professors, experts, books, and prior papers can still be
  mistaken, careless, or copying an earlier mistake;
- the product should therefore treat secondary citations as **leads to verify**,
  not authority to inherit;
- when a citation is doubtful, the preferred behavior is to preserve attribution
  and trace it to the primary source, edition, and original page;
- failure to verify must not be "solved" by silently deleting the citation and
  rewriting the borrowed claim so that it appears original;
- when edition, publisher, page, wording, or metadata disagree, preserve the
  competing provenance and surface the conflict instead of normalizing it away;
- the product's minimum ethical promise to its target user is:
  **尽量引用对，不误后来人。**

Product implication:
the product is not merely a citation finder. It is a small evidence-chain hygiene
tool whose job is to help stop bad citations from being copied forward into the
next paper.

This principle refines D022/D023 and PRODUCT_V0_2. It does not expand scope into
automatic paper writing, plagiarism concealment, or general fact-checking.


## D025 — Current MVP closes on supplied-PDF Golden Case; acquisition stays future

Status: confirmed

On 2026-10-03 the user explicitly narrowed the current MVP finish line after the
source-acquisition experiments.

Durable current-stage decision:
- automatic ebook / primary-source acquisition is **not** required for the current
  MVP;
- the current product promise is: once the user supplies the corresponding PDF,
  the system should reliably trace a secondary quotation/paraphrase + footnote to
  the relevant primary passage and return page provenance, original-page
  screenshot/highlight, and honest citation/provenance information;
- Pilot Case 001 (Weber, 《学术与政治》) is the Golden acceptance case for this
  finish line;
- if the supplied PDF is a different edition/translation from the secondary
  footnote, the product may use it to verify a corresponding passage but must
  surface the edition conflict and must not pretend that it verifies the cited
  edition/page;
- after the Golden Case passes, the next product stage is **UI / visual /
  portfolio-demo packaging**, not source-provider expansion;
- automatic ebook acquisition remains an explicit future extension point;
- later retrieval-strengthening may evaluate reusable GitHub skills/tools around
  CNKI and other literature access/search workflows, especially for fuzzy
  paraphrase / non-verbatim citation tracing, but this does not block the current
  MVP.

Authorized Goal:
`ops/PILOT_CASE_001_WEBER_GOLDEN_DEMO_GOAL_2026-10-03.md`.

This decision supersedes the pending Google Books API-key Human Gate as the
immediate NEXT. It does not prohibit a future bibliographic resolver; it simply
removes acquisition/resolver expansion from the current MVP critical path.


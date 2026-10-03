# Goal — Pilot Case 001 Weber Golden Demo — 2026-10-03

Status: AUTHORIZED by user. This Goal defines the current MVP finish line.

## Product decision

For the current MVP, **primary-source acquisition is not a blocker**.

The product only needs to guarantee the expected verification result **once the user supplies the corresponding PDF**.

Automatic ebook/source acquisition remains a future extension point. Do not add a Google Books key, Z-Library integration, CNKI integration, new provider, scraping route, account, credential, paid service, or acquisition architecture in this Goal.

After this Golden Demo passes, the next stage is product packaging: visual design, UI polish, and demo/portfolio presentation. Retrieval strengthening for fuzzy paraphrases and possible CNKI-oriented skills/tools belongs to a later V1+ evaluation stage.

## Golden real case

Secondary-literature wording:

> 一种人支配人的关系，而这种关系是由正当的（或被视为正当的）暴力手段来支持的。

Recorded secondary source:
王海洲《合法性的争夺：政治记忆的多重刻写》，江苏人民出版社，2008，“作者的话”第1页。

Recorded footnote as written in the secondary source:

> [德]马克思·韦伯.学术与政治[M].冯克利译.北京:外文出版社,1998:41.

The real user-supplied PDF for this Goal is a different Chinese edition:
- Max Weber, 《学术与政治》
- 阎克文译
- 上海人民出版社
- 2021
- ISBN 978-7-208-17140-4
- 263 PDF pages

Important: the PDF is **not** the cited 1998 冯克利 edition. The product must preserve that edition conflict and must not pretend that locating the parallel passage in the 2021 edition verifies the 1998 page-41 bibliographic claim.

## Independently confirmed target passage in the supplied PDF

The semantically corresponding passage crosses two pages in the 2021 edition:

Printed p.105 / PDF p.111 ends with:

> 就像以往历史上的政治集群一样，国家也是一种以正当（就

Printed p.106 / PDF p.112 continues:

> 是说：被视为正当的）暴力为手段的人对人的支配关系。要让国家存在，被支配者就必须服从任何特定时候的支配者宣称他所具有的权威。

This is the Golden target.

## Goal

Starting from the real secondary wording + footnote + the user-supplied PDF, make the normal product flow reliably produce a useful evidence result.

The product must demonstrate that it can move from a **non-verbatim secondary formulation** to the semantically corresponding primary passage in a supplied PDF, then produce traceable original-page evidence.

## Required user-facing result

The normal product path must output:

1. **Matched primary passage**
   - retrieve the above Weber passage despite wording/syntax differences;
   - do not require exact-string identity;
   - show enough surrounding context to make the match intelligible.

2. **Page provenance**
   - identify PDF pp.111-112;
   - identify printed pp.105-106 where available from page images/text;
   - do not fabricate a single-page location when the sentence crosses the page boundary.

3. **Original-page screenshot/highlight**
   - provide highlighted original-page evidence;
   - because the target sentence crosses two pages, either render two highlighted page crops or an honest combined two-page evidence view;
   - highlight the actual matching text, not a synthetic retyped quote.

4. **Edition/provenance conflict**
   - preserve the footnote's claimed 1998 冯克利 / 外文出版社 / p.41 metadata as the secondary source claim;
   - preserve the supplied PDF's 2021 阎克文 / 上海人民出版社 / ISBN 978-7-208-17140-4 metadata as the evidence-file identity;
   - clearly state that the 2021 PDF verifies a corresponding Weber passage, but does **not** by itself verify the claimed 1998 p.41 location or publisher metadata.

5. **Citation output**
   - citation generated from the evidence PDF must use the evidence PDF's confirmed metadata, not silently inherit the secondary footnote's conflicting 1998 metadata;
   - if the product also displays the secondary footnote, label it as the secondary source's recorded citation, not as verified bibliographic truth.

## Retrieval expectation

This case is intentionally not an exact quote.

The pipeline should succeed through the cheapest reliable existing retrieval path first:
- reuse current text-layer extraction/chunking;
- reuse current lexical/embedding/local retrieval if already present;
- improve query construction / normalization / candidate scoring only as needed for this real case;
- do not introduce an LLM reranker, new external service, or large retrieval subsystem unless the existing stack demonstrably cannot solve the case and a Human Gate is opened.

The target is not Weber-specific hardcoding. Any fix must generalize to paraphrase/translation-like wording differences.

## Acceptance tests

P0-A — Real file reaches normal product path
- user-supplied PDF can be placed under the git-ignored private test/work tree and processed through the normal owned-PDF flow;
- no copyrighted PDF bytes are committed to Git.

P0-B — Real paraphrase retrieval
- the exact secondary wording above retrieves the actual passage on PDF pp.111-112 among the top evidence candidates;
- no test fixture may simply inject the known page number into the retrieval result.

P0-C — Traceable evidence
- output includes original-page image evidence with the target text highlighted;
- the page-boundary crossing is represented honestly.

P0-D — Metadata conflict safety
- final output does not claim that the supplied PDF is the 1998 冯克利 edition;
- secondary-claim metadata and evidence-file metadata are both preserved with provenance.

P0-E — Normal UX
- success is visible through the current normal Footnote-first browser flow, not only through a probe script or developer-only route.

P0-F — No regressions
- existing MVP, T003, T004, T006, source-acquisition, and Footnote-first suites remain green;
- add at least one deterministic/local Golden Case regression that can run without committing the copyrighted book. If a full real-PDF regression cannot live in Git, record the private-file smoke command + hash/page evidence and add the strongest non-copyright synthetic/generalized probe possible.

P0-G — Cost/scope
- 0 paid calls;
- no new provider, credential, account, acquisition integration, or major architecture;
- no Weber-title/page hardcoding in production logic.

## Reuse-first

Reuse current accepted components:
- Footnote-first identity/provenance model;
- owned-PDF upload route;
- extraction/OCR/text-layer handling;
- retrieval/evidence objects;
- original-page rendering/highlight;
- citation metadata composition.

Do not reopen source-acquisition architecture in this Goal.

## Stop conditions

Stop and return to Human Gate only if:
- the existing local retrieval stack cannot retrieve the target without a major new model/dependency/architecture;
- the product would need to misrepresent the 2021 edition as the 1998 cited edition;
- a credential, paid service, or new external data source becomes necessary.

Routine bugs, reversible scoring/query changes, page-boundary rendering fixes, and UI continuity fixes should be solved autonomously.

## Definition of done

This Goal is done when a real browser run with the real Pilot Case 001 inputs and the user-supplied PDF visibly produces:

**the corresponding Weber passage + honest pp.105-106 provenance + highlighted original-page evidence + explicit 1998-vs-2021 edition conflict.**

At that point the project may treat this Golden Case as the current MVP acceptance result and move to **UI / visual / portfolio packaging**.

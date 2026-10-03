# Pilot Case 001 — source-resolution safety gate — fix report

Date: 2026-10-03
Status: **COMPLETE** (bounded pilot defect-fix batch under D018 / D024).
Awaiting control-room review; then repeat the exact same real finder step.

Brief: `ops/PILOT_CASE_001_SOURCE_RESOLUTION_SAFETY_GOAL_2026-10-03.md`.
Baseline: Pilot Case 001 GB/T intake fix accepted at `99c9256` + `dd06878`
(local `main` fast-forwarded to `0f4684c` before this work).

Runtime config checked before the work (AGENTS "Model rule"):
`model_provider = custom`, `model = deepseek-flash`, `model_reasoning_effort = low`.
No model call was made by this task; it is pure deterministic code + offline probes.

## Reuse-first gate

Triggered (behaviour change in the acquisition → evidence route) and answered by
**reusing the existing stack first**:

- the repository already contained the safety primitive — `classify_outcome()`
  with `RELEVANCE_FLOOR = 0.5` — but only the *top-level answer* used it, not the
  per-record affordances. The fix wires the existing decision into
  rendering/actionability instead of adding infrastructure;
- Google Books exposes the correct 1998 record but the anonymous API path is
  already observed rate-limited; a key is a credential Human Gate → **not taken**;
- Open Library's no-key edition API and WorldCat (institutional/OAuth) were
  checked and **explicitly deferred** by the brief;
- paper-oriented plugins are not a Chinese book-edition resolver.

Gap left open on purpose: a real bibliographic *resolver* for Chinese editions.
If this same real case still cannot resolve a trustworthy edition after the
safety/query fix, that becomes the pilot evidence that opens that stage.

## What was wrong (real pilot evidence)

Input identity, faithfully parsed from the user's note
`[德]马克思·韦伯.学术与政治[M].冯克利译.北京:外文出版社,1998:41.`:
author `马克思·韦伯`, title `学术与政治`, translator `冯克利`,
publisher `外文出版社`, year `1998`, cited page `41`.

Observed: the finder correctly said only weak matches were found, yet the normal
page still rendered unrelated OpenAlex open-PDF records with a prominent
「下载这个开放 PDF，并用它做核验」 button, and the query shown was the
note's unverified author + generic title. Under D024 that is a safety failure:
*legally downloadable* was silently standing in for *this work*.

Baseline reproduction (archived `HEAD` tree, offline):

```
baseline_queries:                       ['马克思·韦伯 学术与政治']
baseline_outcome (unrelated, score .75): OPEN_PDF_AVAILABLE
baseline_renders_use_found_for_unrelated: True
baseline_has_relevance_gate:             False
baseline_has_identity_anchor:            False
```

## P0-K — weak records are no longer actionable (`tools/source_acquisition.py`)

New, dependency-free, deterministic gate:

- `title_matches(candidate_title, confirmed_titles)` — punctuation/《》- and
  whitespace-insensitive normalization, containment either way, plus a CJK
  bigram-overlap fallback (≥ 0.6) so catalog subtitles/edition markers still
  anchor while generic word overlap does not;
- `identifier_matches(record, identifiers)` — exact DOI/ISBN match;
- `record_relevance(record, anchor)` — requires `match_score >= RELEVANCE_FLOOR`
  **and** (when a title is confirmed) a real title anchor or identifier match;
- `record_actionable(record, anchor)` — relevance **and** evidence eligibility
  (rights/access + a direct PDF URL);
- `classify_outcome(results, report, *, anchor=None)` now drives every branch
  from that gate, so the top-level verdict and the per-record buttons can no
  longer disagree;
- `search_all(..., anchor=None)` also stamps `actionable` /
  `reason_not_actionable` on each record for transparency and for the persisted
  finder payload.

`tools/mvp_app.py` side:

- `render_finder()` computes the anchor from the confirmed identity and splits
  records into shown leads vs. hidden ones; a record that fails the gate is
  moved into a collapsed
  `开发者 / 调试：本次未采用的记录（不构成来源建议）` block and never gets a
  download/use affordance;
- `POST /use_found` re-checks the gate server-side, so posting a weak record's
  index is refused even though no button was rendered for it.

## P0-L — the query prefers stable edition clues (`tools/footnote_parse.py`)

`identity_queries()` now tries `篇名 译者 年份` **first** for a standalone
Chinese book (no separately modelled container), e.g. the real case becomes:

```
['学术与政治 冯克利 1998', '马克思·韦伯 学术与政治']
```

The original parsed fields are never rewritten (asserted by probe), the
container-first ordering for an essay/collected volume is unchanged, and the
author + title query stays in the list as a fallback. No literal query string is
hard-coded; the case produces the above from the parsed identity alone.

`identity_anchor(identity)` was added alongside it: the confirmed work title,
every title variant, any container title, and DOI/ISBN — the set a found record
must genuinely match.

## P1-M — honest empty state

When nothing passes the gate the page says plainly that no trustworthy matching
catalog/full-text candidate was found, that unrelated downloadable PDFs are not
being offered as sources, and that this does **not** mean the work does not
exist. The parsed bibliographic bundle (`复制"查找这一版"`) and the owned-PDF
upload fallback are preserved.

## Verification (0 model calls, $0.00)

New probes (all fail on the pre-fix baseline):

- `tools/source_acquisition_probes.py` **98 → 106** — 8 checks: generic overlap
  is not actionable; below-floor is never actionable; an exact-title candidate
  above the floor stays actionable; an exact DOI anchors; weak and anchored
  outcomes are consistent with the per-record actions; the no-anchor floor rule
  is unchanged; the title anchor is strict on unrelated titles and tolerant of
  edition markers/《》.
- `tools/footnote_first_probes.py` **47 → 58** — 11 rendered-path checks: the
  real GB/T note now searches `学术与政治 冯克利 1998`; the unrelated
  downloadable OpenAlex record renders no download/use action; the honest empty
  state and the collapsed debug list are rendered; the upload + edition-bundle
  fallback survive; `POST /use_found` refuses that record server-side; an
  anchored record stays actionable and is the only one rendered with a download
  form; query planning never mutates the parsed identity and keeps the
  author+title fallback; the anchor is built from the confirmed title.

Baseline-failure evidence (probes run against the archived pre-fix tree): all 7
checks that ran before the probe aborted were `FAIL`, and the run aborted because
the pre-fix build actually invoked a download of the unrelated PDF
(`AssertionError: an unrelated record must never be downloaded`). The pre-fix
tree also has no `record_actionable` / `identity_anchor`, so the gate checks
cannot pass by construction.

Full regression rerun (0 model calls, $0.00):

- `mvp_probes` **70/70**
- T003 **15/15**
- T004 **16/16**
- T006 **5/5**
- `source_acquisition_probes` **106/106**
- `footnote_first_probes` **58/58**

The single-network-call invariant is preserved (`sa.search_all(` still appears
once in `mvp_app.py`, reached only from `POST /find`; the pipeline never imports
the finder) and the accepted evidence/highlight routes are unchanged. GitHub has
no Actions / commit-status checks for this repository, so these counts are Codex
local execution evidence, not an independent CI rerun.

## Boundaries honored

No new provider, credential, paid service, dependency, model call, RAG/evidence
stack, or architecture; no broad scraping or multi-query fan-out; the normal UI
stays simple. Lawful source-acquisition guardrails and the evidence/highlight
pipeline are unchanged. D019/D022/D023 and the D024 principle are unchanged.
Open Library, WorldCat, a Google Books key and any Chinese-catalogue provider
remain deferred.

## Definition of done

Met: the normal product now prefers 「暂时找不到可信匹配的版本；请上传或查找这一版」
over offering an unrelated open PDF merely because it is downloadable.

## Live rerun of the same real finder step on the safe build

The exact real citation was run again through the real `POST /find` route
(in-process product server, live public OA APIs, 0 model calls, $0.00):

```
planned queries:  ['学术与政治 冯克利 1998', '马克思·韦伯 学术与政治']
anchor:           {'titles': ['学术与政治'], 'identifiers': {}}
query shown:      学术与政治 冯克利 1998
outcome:          USER_UPLOAD_REQUIRED
                  「只找到与查询弱相关的记录，没有可用作页码可核验证据的开放 PDF。」
renders a download/use action: False
honest empty state: True   edition bundle kept: True   upload fallback kept: True
debug block present: True
```

Provider report: OAPEN/DOAB HTTP 404, Google Books HTTP 429 (anonymous daily
quota exhausted), OpenAlex 6 records, Internet Archive 1, 中文维基文库 1.

The 8 returned records scored 0.00–0.125 and were **all** withheld from the
normal UX with an explicit reason; the OpenAlex hits were plainly unrelated
(`中国古代政治地理思想探究`, `遥感科学与技术交叉学科知识和教学体系研究`, …),
which is exactly the failure the pilot reported. Before the fix this same step
announced `OPEN_PDF_AVAILABLE` and rendered a download button for such a record.

Direct pilot evidence for the deferred stage: **the same real case still cannot
resolve a trustworthy edition.** Google Books holds the correct 1998 record but
the anonymous path is quota-blocked, and the current providers have no
zero-friction Chinese book-edition lookup. Adding that resolver (Open Library /
WorldCat / a Google Books key / another Chinese catalogue) remains a Human Gate
that this evidence now justifies evaluating.

## NEXT

Repeat the exact same real Pilot Case 001 finder step in the browser with the
citation unchanged, and record whether a trustworthy edition can actually be
resolved. If it still cannot, that is the direct evidence required to open a
dedicated bibliographic-resolver stage (with its own Reuse-First evaluation and
Human Gate).

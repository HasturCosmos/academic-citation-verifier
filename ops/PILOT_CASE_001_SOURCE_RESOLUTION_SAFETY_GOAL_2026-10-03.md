# GOAL — Pilot Case 001 source-resolution safety gate — 2026-10-03

Status: AUTHORIZED bounded pilot defect-fix under D018 / D024.

Baseline: Pilot Case 001 GB/T intake fix accepted at commits `99c9256` + `dd06878`.
Trigger: the same real browser case after identification succeeded.

## Real pilot evidence

Input identity (faithfully parsed from the user's note):
- author: `马克思·韦伯`
- title: `学术与政治`
- translator: `冯克利`
- publisher: `外文出版社`
- year: `1998`
- cited page: `41`

Observed finder behavior:
- the finder correctly classified the overall outcome as weak / no trustworthy matching open source;
- nevertheless the normal page still rendered obviously unrelated OpenAlex open-PDF records and gave each a prominent “下载这个开放 PDF，并用它做核验” button;
- the query shown was essentially the typo-bearing author + title, so unrelated papers containing generic “学术 / 政治” terms ranked above zero;
- this creates a D024 safety failure: access eligibility can currently make an unrelated PDF actionable even when bibliographic relevance is below the declared relevance floor.

Do not encode the known correct Weber bibliography into code. The product must generalize.

## Reuse-first scan

Current repository:
- keep `source_acquisition.py` and the existing providers;
- `classify_outcome()` already has `RELEVANCE_FLOOR=0.5` and correctly distinguishes weak records;
- the defect is that rendering/actionability does not enforce that relevance decision.

External mature options checked:
- Google Books contains an exact public bibliographic record for the 1998 冯克利 edition, but the current anonymous API path is already observed as rate-limited/unreliable; adding a Google API key is a credential Human Gate and is NOT authorized here.
- Open Library offers public, no-key, edition-aware APIs suitable for low-volume book lookup, but its coverage of this exact 1998 Chinese edition is incomplete in quick checks. It remains a candidate for a later resolver experiment, not part of this bounded fix.
- WorldCat Search API requires institutional subscriptions / OAuth credentials, so it is not a zero-friction MVP route.
- available academic-paper plugins (Consensus / Scite) are paper-focused, not a Chinese book-edition resolver, and are not appropriate for this product path.

Decision: first reuse the current stack and fix its unsafe relevance/actionability behavior. Do not add a provider yet.

## P0-K — weak records must never be actionable in normal UX

A record may offer the normal “download / use for verification” action only when:
- it is evidence-eligible by rights/access rules; AND
- it passes bibliographic relevance for the confirmed identity.

At minimum:
- records below `RELEVANCE_FLOOR` cannot render a download/use button;
- if a confirmed title exists, normal actionability must require a title anchor (normalized candidate title materially matches the confirmed title) OR an exact strong identifier match (ISBN/DOI where present);
- generic term overlap such as “学术”“政治” is not enough;
- weak records may be omitted from normal UX or moved into a collapsed developer/debug section, but must not be presented as plausible source choices.

## P0-L — query planning must prefer stable edition clues over a suspect author string

Do not silently correct the source fields.

For Chinese book-like identities with a confirmed title:
- build the primary search query around the title first;
- use translator and year as supporting terms when available;
- do not let an unverified author spelling or publisher be the only anchor that can prevent retrieval;
- preserve all original fields and provenance separately so later conflicts remain visible.

For this real case, a query shaped like `学术与政治 冯克利 1998` is acceptable; do NOT hard-code that literal string or Weber-specific logic.

Keep the normal lookup bounded. Do not broaden into whole-web search or unbounded multi-query fan-out in this fix.

## P1-M — honest empty state

If no record survives the relevance/title-anchor gate:
- say plainly that no trustworthy matching catalog/full-text candidate was found;
- keep the parsed bibliographic bundle and upload fallback;
- do not claim the source does not exist;
- do not expose unrelated PDFs as next-step buttons.

## Acceptance probes

Add zero-cost probes that fail on the current baseline:
1. an evidence-eligible OpenAlex PDF with low score / no confirmed-title anchor is not actionable;
2. overall weak-result state and per-record actions are consistent;
3. an exact-title candidate above the relevance floor remains actionable when rights/access rules also pass;
4. query planning for a Chinese book with title + translator + year prefers those stable fields and does not mutate the original identity;
5. current no-PDF upload fallback and “查找这一版” bundle remain intact;
6. all existing 47 Footnote-first probes and all prior regression suites remain green;
7. no new provider, credential, dependency, model call, or architecture.

## Explicitly deferred

Do NOT add Open Library, WorldCat, a Google Books key, browser scraping, or any new Chinese-catalog provider in this task.

If the same real case still cannot resolve a trustworthy edition after this safety/query fix, that becomes direct pilot evidence for a dedicated bibliographic-resolver stage and Reuse-First evaluation.

## Definition of done

The normal product must prefer “I cannot find a trustworthy matching edition yet; upload/find this edition” over offering an unrelated open PDF merely because it is downloadable.

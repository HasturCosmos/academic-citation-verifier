# Pilot Case 001 — Chinese GB/T-footnote intake + visible retry — fix report

Date: 2026-10-03
Status: **ACCEPTED / PASS** — control-room code review completed 2026-10-03; resume the exact same real pilot case for browser-level confirmation.

Brief: `ops/PILOT_CASE_001_GBT_FOOTNOTE_FIX_GOAL_2026-10-03.md` (authorized
routine defect-fix batch under D018).
Baseline: Footnote-first V0.2 pilot-ready at `ecbd2c9fbbab16c3da9fa230a8b316e5329f2a53`.

## Reuse-first gate

This is a bounded extension of the existing deterministic parser, not a new
capability: no new reusable subsystem, retrieval layer, resolver, dependency,
provider, credential, model call or architecture. The gate is therefore not
triggered; the only reuse is the in-repo `tools/footnote_parse.py` parser itself.

## What was wrong

The first real thesis footnote
`[德]马克思·韦伯.学术与政治[M].冯克利译.北京:外文出版社,1998:41.`
was not recognized as author + title, because the deterministic Chinese parser
primarily expected `作者《…》` / quoted-title forms. `POST /identify` therefore
returned "还需要一点脚注线索". A retry with the shorter clue
`[德]马克斯·韦伯,学术与政治` rendered the same insufficient-clue page with no
explicit failure message, so the retry button looked dead.

## P0-I — common Chinese bibliographic punctuation (`tools/footnote_parse.py`)

Added `_parse_gb_t_cjk()` plus GB/T-style regexes; the legacy `《…》` / quoted
parser is left untouched and owns every note that actually uses `《…》`:

- optional nationality prefix `[德]` / `［德］` is stripped before author parsing
  and never pollutes the author; it is not silently "corrected" into the name;
- `作者.题名` / `作者,题名` / `作者，题名` when a work-type marker such as `[M]`,
  `[J]`, `[C]`, `[D]` follows the title (marker also sets the work type);
- the shorter markerless clue `[德]马克斯·韦伯,学术与政治` yields author + title;
- translator forms separated by ASCII or Chinese punctuation, e.g. `.冯克利译.`;
- `出版地:出版社` / `出版地：出版社`;
- `年份:页码` / `年份：页码` (e.g. `1998:41`).

The parser extracts exactly what the note says. For the pilot fixture it returns
author `马克思·韦伯`, title `学术与政治`, translator `冯克利`, publisher
`外文出版社`, year `1998`, cited page `41` — including the note's own
`外文出版社`/`41`, even though catalogs may disagree. Any such conflict stays a
later evidence conflict; it is never hard-coded into parsing.

## P1-J — visible retry feedback (`tools/mvp_app.py`)

`POST /identify` now renders an explicit message on the insufficient-clue page
when a non-empty note still yields no usable handle: it names exactly which of
篇名/书名、作者、DOI、ISBN are still missing, keeps the footnote editable, and
still refuses to launch a broad search. The initial (empty-note) page is
unchanged and distinct from a failed retry.

## Verification (0 model calls, $0.00)

`tools/footnote_first_probes.py` grew from 38 to **47** checks; the 9 new checks
all fail on the `ecbd2c9` baseline:

1. the exact real-pilot note parses the expected six fields faithfully;
2. the parser keeps the note's own author/publisher/page (no silent correction);
3. the short clue `[德]马克斯·韦伯,学术与政治` yields useful author + title;
4. the mixed ASCII/Chinese punctuation variant still parses;
5. no `《…》` / quoted Chinese or Western parsing regression;
6. the real note reaches the identity screen through the HTTP `/identify` route;
7. an insufficient retry returns a visible explanatory message;
8. the initial insufficient page stays distinct from the retry page;
9. the extended parser introduces no network/model/dependency.

Full rerun of every existing suite (0 model calls, $0.00):

- `mvp_probes` **70/70**
- T003 **15/15**
- T004 **16/16**
- T006 **5/5**
- `source_acquisition_probes` **98/98**
- `footnote_first_probes` **47/47**

The single-network-call invariant is preserved (`sa.search_all(` still appears
once in `mvp_app.py`, reached only from `POST /find`; the pipeline never imports
the finder) and the accepted evidence/highlight routes are unchanged.

## Boundaries honored

No new provider, credential, paid service, model call, dependency, RAG/evidence
stack, or architecture. No broad scraping. Lawful source-acquisition guardrails,
the evidence/highlight pipeline and the simple normal UI are unchanged.
D019/D022/D023 and the D024 verification principle are unchanged.

## Definition of done

Met: the first real pilot citation passes the identification screen as
conventionally written, and a failed retry visibly tells the user what remains
missing instead of looking like a dead button.

## NEXT

Resume the exact same real Pilot Case 001 in the browser, using the citation
unchanged. Confirm that the identification screen is reached and that the source
text is extracted faithfully. Then continue the workflow far enough to expose
the next real bottleneck, if any.

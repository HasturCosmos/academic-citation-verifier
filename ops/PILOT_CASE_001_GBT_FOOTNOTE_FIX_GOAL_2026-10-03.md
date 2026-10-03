# GOAL — Pilot Case 001: Chinese GB/T-style footnote intake + visible retry — 2026-10-03

Status: AUTHORIZED routine pilot defect-fix batch under D018.

Baseline: Footnote-first V0.2 accepted / pilot-ready at commit `ecbd2c9fbbab16c3da9fa230a8b316e5329f2a53`.
Pilot trigger: first real-user case after acceptance.

## Pilot evidence

Real footnote shape (bibliographic input only; do not encode the user's surrounding thesis prose):

`[德]马克思·韦伯.学术与政治[M].冯克利译.北京:外文出版社,1998:41.`

Observed:
- `POST /identify` returned “还需要一点脚注线索”;
- retrying with `[德]马克斯·韦伯,学术与政治` visually appeared to do nothing because the parser still considered the clue insufficient and the same page was rendered without an explicit retry-failure message.

Root cause in current deterministic parser:
- Chinese author parsing expects the author to be followed by `《…》` or a quoted title;
- common Chinese reference-manager / GB/T-like forms `作者,题名[M].译者译.出版地:出版社,年份:页码` are not recognized as author+title;
- ASCII period-delimited translator segments and trailing `year:page` are not first-class parsing shapes.

This is a real pilot defect, not a new architecture need.

## Required fix

### P0-I — accept common Chinese bibliographic-reference punctuation

Extend the existing deterministic parser only. No model and no new parser dependency.

At minimum:
- optional nationality prefix such as `[德]` before the author;
- `作者.题名`, `作者,题名`, or `作者，题名` when a bibliographic type marker such as `[M]`, `[J]`, `[C]`, `[D]` etc. follows the title;
- also allow the shorter clue `[德]马克斯·韦伯,学术与政治` to yield author + title when the two comma-separated fields are unambiguous;
- translator forms split by ASCII or Chinese punctuation, e.g. `.冯克利译.`;
- publisher in `出版地:出版社` / `出版地：出版社`;
- year + cited page in `1998:41` / `1998：41`;
- preserve explicit source text as written; do not “correct” publisher/page from outside knowledge during parsing.

For the real pilot fixture above, expected deterministic fields:
- author: `马克思·韦伯` (faithfully parse the source as written; nationality prefix may be stored separately or ignored, but must not pollute author);
- title: `学术与政治`;
- translator: `冯克利`;
- publisher: `外文出版社` (parse what the note says, even if later source-resolution evidence conflicts);
- year: `1998`;
- cited_page: `41`.

### P1-J — retry must visibly respond when clues are still insufficient

When `/identify` receives a non-empty retry but still cannot build a useful identity:
- render a visible message explaining which minimum handles are still missing (author/title/DOI/ISBN);
- keep the user's text editable;
- do not silently render an indistinguishable page;
- do not broad-search.

If the newly supplied clue *is* parseable, proceed normally.

## Acceptance probes

Add zero-cost probes that fail on the accepted baseline:
1. exact real-pilot footnote above, including the `作者.题名[M]` punctuation and the written form `马克思·韦伯`, parses the expected six fields without silently correcting the author name;
2. short clue `[德]马克斯·韦伯,学术与政治` yields useful author + title;
3. mixed ASCII/Chinese punctuation variant still parses;
4. an insufficient retry returns a visible explanatory message rather than an indistinguishable page;
5. no existing `《…》` / quoted Chinese or Western parsing behavior regresses;
6. no new network call/provider/dependency/model call is introduced.

Rerun all existing suites, including all 38 Footnote-first probes.

## Product/evidence boundary

External research during the pilot suggests that the bibliographic record itself may contain a publisher/page error. Do **not** hard-code that correction into the parser. The parser's job is to faithfully extract what the note says. Any later mismatch against catalog/source metadata must remain a visible evidence conflict.

## Constraints

- no new provider, credential, paid service, model call, dependency, RAG/evidence stack, or architecture;
- no broad scraping;
- preserve lawful source-acquisition guardrails and existing evidence/highlight pipeline;
- keep normal UI simple;
- D019/D022/D023 remain unchanged.

## Docs / state

Update this pilot case in PROJECT_STATE / TASK_QUEUE / RUN_LOG and write a short fix report.

## Definition of done

The first real pilot citation can pass the identification screen using the citation as it is conventionally written, and a failed retry visibly tells the user what remains missing instead of looking like a dead button.

# PRODUCT_V0_1

Status: CONFIRMED by user on 2026-10-01.

## Product name

二流文科生的二手文献

## One-sentence definition

用户把二手文献中的引用、转述或相关页面交给系统；系统利用正文语义与各种可能不可靠的线索，在当前可访问资料源中寻找对应的中文一手文献，并把中文版原文、原页高亮截图、页码和可复制引用直接展示给用户。

## Product philosophy

- 不替用户写论文；替用户减少繁琐的一手文献追踪劳动。
- 核心价值是 secondary literature -> primary evidence。
- 证据优先于 AI 意见；允许“不确定”和“当前无法核验”。
- 产品适应用户手里的不完整、混乱、甚至错误线索，而不是要求用户先整理成标准数据库表单。

## Inputs

Primary input supports all of:
- pasted text;
- uploaded secondary-source PDF;
- uploaded image / photographed book page.

Optional free-form hints field may contain:
- footnote text;
- author / title / year / page / translator / publisher;
- user's memory, description, topic clue, or other uncertain information.

Hints are never treated as authoritative facts.

For a full page containing multiple possible citations/paraphrases, the system should detect candidate items and allow single-select, multi-select, or select-all before retrieval.

## Evidence priority

1. Actual Chinese primary-source page evidence returned by the system.
2. Semantic content of the secondary-source passage.
3. Footnotes / bibliographic clues.
4. User-supplied memories or descriptions.

Footnotes and OCR output may be wrong. A conflicting page number or citation clue must not prematurely exclude a semantically plausible source.

## Source scope

- Product scope is author-agnostic and discipline-agnostic.
- Coverage is determined by the full text that the currently connected/available source adapters can access.
- Weber material is an evaluation set, not a product whitelist.
- If the current source set lacks sufficient full text, report only that the current sources cannot verify the claim; do not imply the work does not exist.

## Retrieval output

When a likely corresponding Chinese original passage is found, show:
- copyable Chinese original text;
- original-page screenshot with the relevant passage highlighted;
- page number;
- bibliographic metadata that is actually known;
- copy buttons for a basic Chinese footnote citation and a basic reference-list citation.

Do not invent missing bibliographic metadata.

Example acceptable base citation shape:
`[德]马克思·韦伯.经济与社会（第一卷）[M].阎克文译.上海:上海人民出版社,2019:118-119.`

Multiple citation styles are deferred until user demand justifies them.

## Multiple candidates and editions

- If several passages may correspond, do not force a winner. Present the plausible candidates and let the user choose.
- If several Chinese editions/translations contain plausible corresponding passages, show all of them; do not rank editions as "best".
- Version differences are information, not a product value judgment.

## Progressive disclosure

Default result view should be compact:
- number of Chinese editions found;
- number of candidate passages per edition.

Users expand an edition/candidate to inspect:
- original text;
- page screenshot/highlight;
- page number;
- citation controls.

## AI judgment and cost

AI/retrieval judgment is necessary in the backend to narrow a large corpus to plausible candidates.

MVP default output should not spend tokens on long interpretive essays. Minimal matching rationale may be shown when useful.

Detailed analysis of whether the secondary author misquotes, exaggerates, omits qualifications, or mistranslates is a later/on-demand capability.

## Failure states

Distinguish at least:
1. reliable corresponding evidence found;
2. multiple plausible candidates found;
3. target text exists in current sources but no reliable corresponding passage was found;
4. current sources do not contain sufficient primary-source full text to verify.

Never manufacture a match merely to return an answer.

## MVP boundary

The MVP may use a limited set of currently available source adapters/resources. It does not need to solve universal literature acquisition before the first demo.

The near-term goal is a real runnable vertical slice that the user can personally use, demonstrate, open-source, and put into an internship portfolio.

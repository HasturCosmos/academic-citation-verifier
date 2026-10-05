# M3 FRESH CASE A — REAL-WORLD EVALUATION REPORT

Date: 2026-10-05
Status: **FIRST PASS COMPLETE / HUMAN GOLD JUDGMENT PENDING**
Branch: `m3-real-evaluation`
Frozen product base: `main@270acaf`

## 1. Case provenance

Secondary source:
- [美]弗里茨·林格，《韦伯学术思想评传》，马乐乐译，北京大学出版社，2011，第94页。
- Footnote: [14] "Kritische Studien," 271, 277, 282-85.

Secondary paraphrase supplied by the user:
> 韦伯拒绝了重现各个具体条件(它们合起来作为后果的充分条件)之总体这一设想，相反，他大致概述了由克里斯所提出的分析策略。一组事前状况必须以某种方式在概念上分离出来，它们或强或弱地“倾向于”待解释的结果。为此目的所需要的可能性判断，通常而言没法定量;但是，我们能够聚焦于选择出来的潜在“原因”，并比较附加状况的范围-在伴随这些附加状况的前提下，潜在“原因”将会(或将不会)导致待说明的结果。

Primary source:
- user-supplied PDF of Max Weber, 《社会科学方法论文集》, 阎克文/姚燕译.
- PDF has 310 sequence pages.
- User explicitly requested PDF sequence pages only; no printed-page mapping is required for this case.
- private source SHA-256: `EAE53233C9194F7D2488B7B8AA0C51CA47ABB8BC3ACAD2C3FD33AA4004C5EFF3`.
- source bytes: 14,200,158.
- private copy: `data/private/M3-FRESH-A/source/fresh_a_source.pdf` (git-ignored).

The private project copy was hash-verified against the conversation-uploaded PDF bytes.

## 2. Frozen run

Command surface: accepted `tools/mvp_app.py --run-once`.

Frozen settings:
- retrieval mode: local;
- OCR mode: auto;
- k: 10;
- no product-code change;
- no ranking tuning;
- no pre-run manual source-page lookup.

Observed:
- route: `text_layer`;
- source pages: 310;
- chunk count: 903;
- candidates recorded: 13 (hint-assisted + retrieval candidate assembly);
- located: 0;
- highlight images: 0;
- product state: `no_corresponding_passage`;
- model calls: 0;
- cost: USD 0.00;
- index: 92.0 s;
- retrieval: 0.4 s;
- evidence localization: 2.1 s;
- total measured wrapper wall time: 101.8 s;
- index cache hit: false.

## 3. Retrieval result before localization failure

Although the final product state was negative, retrieval reached several conceptually relevant source regions:

- rank 1 -> PDF pp.140-141;
- rank 4 -> PDF p.130;
- rank 5 -> PDF p.130;
- rank 6 -> PDF pp.126-127;
- rank 9 -> PDF p.129;
- rank 10 -> PDF p.131.

These passages discuss the same cluster present in the secondary paraphrase:
- infinite causal conditions / sufficiency;
- von Kries;
- isolating selected conditions;
- objective-possibility judgments;
- inability to quantify the relation in ordinary historical cases;
- comparing ranges / degrees of conditions that promote possible results;
- totality of conditions and causal reconstruction.

Therefore the first-pass failure must not be summarized as “retrieval found nothing”.

## 4. Important case structure finding

The secondary paragraph appears to synthesize multiple Weber passages rather than quote/paraphrase one contiguous source paragraph.

This is also structurally consistent with the supplied secondary footnote, which cites multiple original locations: 271, 277, 282-85.

Preliminary source inspection after the frozen run identifies at least three evidence clusters:
- PDF pp.140-141 — infinite conditions, “sufficient” conditions, von Kries;
- PDF pp.127-128 — isolating possible-result conditions, comparing ranges, non-quantifiability;
- PDF pp.130-131 — possibility judgment, isolating conditions, totality of conditions, promoting/impeding results and alternative condition combinations.

PDF pp.118-119 also supplies closely related context on selecting causally important components from infinitely many determining factors.

This is an M3 product finding: one long secondary paraphrase may require a **multi-passage evidence set**, not a forced single-passage winner.

## 5. Localization failure diagnosis (no product change)

Every candidate ended as `unmatched` even though its retrieval page text came from this PDF.

A zero-change diagnostic compared candidate text with PDFium page text.

Result:
- current compact exact match: false for all candidates;
- after Unicode NFKC normalization, exact compact match becomes true for ranks 3, 4, 5, 9 and 13;
- ranks 4, 5 and 9 are in the relevant Weber causal-methodology region.

Each candidate contains dozens of characters altered by NFKC (e.g. compatibility/radical CJK forms).

Conclusion:
**Confirmed localization robustness bug: the evidence locator's current normalization is too narrow for this PDF text layer.**
This is distinct from retrieval quality.

Other candidates still fail after NFKC, so NFKC is a confirmed partial fix, not yet a complete localization solution.

No code was changed during this diagnosis.

## 6. First-pass M3 measurement

| Metric | First-pass result |
| --- | --- |
| Top-1 contains relevant source region | **YES, preliminary** (rank 1 -> pp.140-141) |
| Top-3 contains relevant source region | **YES, preliminary** |
| Top-5 contains relevant source region | **YES** (pp.130 and pp.140-141 represented) |
| Top-10 contains relevant source region | **YES, multiple clusters** |
| Human-confirmed best evidence set | **PENDING** |
| Page localization | **FAIL in product output** |
| Highlight correctness | **NOT MEASURABLE (0 highlights)** |
| False-positive candidates | present (e.g. ranks 2/3 in distant value-judgment discussion) |
| Claim support judgment | **PENDING HUMAN GOLD** |
| Important qualifier/context | likely multi-passage synthesis; final judgment pending |
| Uncertainty honesty | PASS — product did not fabricate pages/highlights |
| Cost | USD 0.00 |
| First-run latency | 101.8 s incl. cold indexing |

## 7. Human Gate — gold judgment

Before any bug fix, ask the user to review the independently surfaced primary-source clusters and confirm whether the core corresponding evidence is:

A. PDF pp.140-141;
B. PDF pp.127-131;
C. both A + B as a multi-passage evidence set;
D. another interpretation.

Only after this gold judgment should a bounded localization-fix Goal be considered.

## 8. UNIQUE NEXT

Obtain the user's gold judgment for Fresh Case A.

Do not tune retrieval and do not patch localization before the gold judgment is recorded.

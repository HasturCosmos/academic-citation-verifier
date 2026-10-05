# M3 FRESH CASE B — REAL-WORLD EVALUATION REPORT

Date: 2026-10-05
Status: **FIRST PASS COMPLETE / HUMAN GOLD JUDGMENT PENDING**
Branch: `m3-real-evaluation`
Frozen product base: `main@270acaf`

## 1. Case provenance

Secondary source:
- [美]弗里茨·林格，《韦伯学术思想评传》，马乐乐译，北京大学出版社，2011，第89页。
- Footnote: Weber, "Objektivitait," 176-178; "Kritische Studien," 237-43.

Secondary paraphrase supplied by the user:
> 事实上，韦伯追随李凯尔特区分了“主要的”历史事实与“次要的”历史事实，前者指那些自身就是重要的、有意义的事实，后者则属于前者的原因。另一方面，韦伯拒绝把历史定义为是因果有效的，因为历史事物的因果联系也是无穷无尽的，与此同时，许多历史结果都微不足道。因此，无论历史学家们依据什么样的解释手段，他们依然需要判断哪些是有意义的，哪些是没有意义的，以选定他们所试图说明的个体性后果。

Primary source:
- same user-supplied Max Weber 《社会科学方法论文集》 PDF as Fresh Case A.
- SHA-256: `EAE53233C9194F7D2488B7B8AA0C51CA47ABB8BC3ACAD2C3FD33AA4004C5EFF3`.
- 310 PDF sequence pages.
- User requested PDF sequence pages only; no printed-page mapping.

## 2. Frozen run

Accepted `tools/mvp_app.py --run-once`.

Frozen settings:
- retrieval mode: local;
- OCR mode: auto;
- k: 10;
- no product-code change;
- no ranking tuning;
- exact user-supplied secondary wording and footnote passed to the runner.

Observed:
- route: `text_layer`;
- page count: 310;
- chunk count: 903;
- candidate objects: 11;
- located: 0;
- highlight images: 0;
- product state: `no_corresponding_passage`;
- model calls: 0;
- cost: USD 0.00;
- index: 64.2 s;
- retrieval: 0.3 s;
- evidence localization: 2.2 s;
- measured run ≈75 s including wrapper overhead.

The temporary wrapper ended with a Windows GBK printing error after the product process had already finished and written `result.json`. The evaluation result itself is intact.

## 3. Retrieval findings

The semantic retrieval result is strong for one major evidence cluster.

Highly relevant candidates:
- rank 1 -> PDF p.107;
- rank 2 -> PDF p.107;
- rank 7 -> PDF pp.110-111;
- rank 9 -> PDF p.110.

These passages explicitly discuss:
- two kinds of historical facts;
- historical individuals vs historical causes;
- Rickert's distinction between “primary” and “secondary” historical facts;
- causal regression;
- cultural individuality;
- value relations and the definition of historical objects.

Additional nearby candidates:
- rank 5 -> PDF p.89;
- rank 10 -> PDF pp.89-90.

These discuss:
- “historical” as what has produced consequences;
- the infinite number of individual events;
- historical interest / selection.

Therefore the first half of the Ringer paraphrase is retrieved very strongly at Top-1.

## 4. Post-run source inspection (no product change)

Independent source inspection after the frozen run identifies another major evidence cluster at:

- PDF pp.43-44.

This passage states, in substance:
- only a finite portion of infinitely rich reality is meaningful;
- the causes determining any individual event are infinite in number and form;
- there is no intrinsic marker telling us which part alone deserves consideration;
- historical inquiry selects portions related to cultural value ideas;
- an all-inclusive causal regression from any concrete phenomenon is not merely impractical but absurd;
- we grasp only the “major” components of an event for causal attribution.

This cluster directly supports the latter half of the secondary paraphrase:
- causal connections are inexhaustible;
- not every result is meaningful;
- historians must select what is meaningful / worth explaining.

However, PDF pp.43-44 did **not** appear in the frozen Top-10 candidate list.

## 5. Case structure finding

Fresh Case B is again a **multi-passage / multi-essay synthesis**.

The supplied footnote itself cites two Weber essays:
- “Objektivitait” 176-178;
- “Kritische Studien” 237-43.

The frozen retrieval strongly surfaces the “Kritische Studien” style cluster around PDF pp.107-111, but does not surface the separate “Objektivität” cluster around PDF pp.43-44 in Top-10.

This is not classified as a blocker under the current MVP product bar:
the product is a reference / verification assistant and is not required to exhaustively recover every supporting source passage.

## 6. Localization failure diagnosis

As in Fresh Case A:
- all candidates are `unmatched`;
- zero highlights are emitted;
- this is not evidence that the passages are absent.

NFKC normalization alone restores an exact page-text match for rank 9 (PDF p.110), confirming that Unicode compatibility forms are again one real localization failure mode.

Most other candidates still fail after NFKC, so the localization issue is broader than NFKC alone.

No code was changed.

## 7. First-pass M3 measurement

| Metric | First-pass result |
| --- | --- |
| Top-1 contains relevant source region | **YES** — PDF p.107 |
| Top-3 contains relevant source region | **YES** |
| Top-5 contains relevant source region | **YES** |
| Top-10 contains relevant source region | **YES, multiple passages around pp.89-111** |
| All major supporting clusters recovered in Top-10 | **NO** — pp.43-44 absent |
| Human-confirmed best evidence set | **PENDING** |
| Page localization | **FAIL in product output** |
| Highlight correctness | **NOT MEASURABLE (0 highlights)** |
| Claim support judgment | **PENDING HUMAN GOLD** |
| Uncertainty honesty | PASS — no fabricated page/highlight |
| Cost | USD 0.00 |
| First-run latency | ~75 s incl. cold indexing |

## 8. Human Gate — gold judgment

Please confirm which interpretation best represents this secondary paragraph:

A. PDF pp.107-111 are sufficient as the core corresponding evidence;
B. PDF pp.43-44 are the main corresponding evidence;
C. both PDF pp.43-44 + pp.107-111 form the correct multi-passage evidence set;
D. another interpretation.

The user's previously confirmed product bar remains in force:
do not optimize semantic retrieval in the current milestone.

## 9. UNIQUE NEXT

Obtain the user's gold judgment for Fresh Case B.

Do not tune semantic retrieval or patch localization before the gold judgment is recorded.

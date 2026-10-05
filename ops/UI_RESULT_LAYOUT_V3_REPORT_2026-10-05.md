# UI Result Layout V3 Report — 2026-10-05

Status: **IMPLEMENTED + REGRESSION PASS / USER VISUAL ACCEPTANCE PENDING**

Branch: `ui-result-page-v0`
Base: `9dd2bee`

## User-confirmed V3 adjustments

- Product title changed to **二流文科生的二手文献引用助手**.
- Title uses a restrained text-first brand treatment, not decorative art lettering.
- Single-PDF source area compressed so the bibliographic/candidate area rises into the first screen.
- Removed the normal-user sentence "当前核验所用的一手文献 · PDF 文本层（默认路径）".
- Source card keeps only filename + compact replace-PDF action. OCR provenance remains a compact badge only when OCR is actually used.
- Bibliographic metadata is cleanly separated from edition conflicts.
- Edition conflicts are now a standalone yellow warning card directly below bibliographic metadata.
- Right-side candidate detail removes the status/header/default-view explanation block.
- Right side now contains only:
  1. original page + highlight;
  2. corresponding Chinese source text;
  3. copyable footnote + bibliography.
- PDF sequence provenance remains as a small caption under the original-page images.

## Real Weber visual check

Rendered at 1600×1400:
- no large blank vertical gap below the source card;
- bibliography and candidate list start immediately below the compact source row;
- independent yellow conflict module is visually distinct;
- right panel begins directly with source-page evidence;
- title clearly states product identity;
- candidate selection semantics remain intact.

## Verification

- MVP/UI probes: **90/90**
- T003 localization: **15/15**
- T004 evidence object: **16/16**
- T006 OCR: **5/5**
- source acquisition: **106/106**
- Footnote-first: **58/58**

No retrieval/ranking/model/provider/OCR architecture change.
No new frontend dependency.
No private source data or screenshots added to Git.

## UNIQUE NEXT

User visually reviews the live Weber V3 result page.

Do not merge to `main` until accepted.

# UI Result Layout V4 Report — 2026-10-05

Status: **IMPLEMENTED + REGRESSION PASS / USER VISUAL ACCEPTANCE PENDING**

Branch: `ui-result-page-v0`
Base: `ee64cba`

## User-confirmed V4 corrections

This batch is a bounded correction of V3, not a redesign.

1. **Title position**
   - The full product title remains “二流文科生的二手文献引用助手”.
   - The title now lives inside the left workspace and is centered above the source area, matching the earlier accepted visual relationship.
   - Removed the oversized transformed result canvas that caused horizontal page scrolling and made the title look shifted to the right.

2. **Candidate list spacing**
   - Restored the roomier V2-style candidate-row composition.
   - Status chip, printed page, selected marker and “展开查看” remain on one readable line at the target desktop width.
   - Selected state remains visually explicit.

3. **Right detail: content only**
   Removed the normal-user labels:
   - “原页 + 高亮”
   - “PDF 顺序页 …”
   - “对应中文版原文”
   - “一键复制引用”

   The right detail now presents only:
   - original highlighted page images;
   - corresponding Chinese source text;
   - footnote and bibliography copy blocks.

   PDF sequence provenance remains in the evidence data/object model but is not displayed as normal-user explanatory copy.

4. **Independent right-column scrolling**
   - Right detail is a sticky, height-bounded scroll container.
   - It uses `overflow-y:auto` and `overscroll-behavior:contain`.
   - Real browser rendering shows a dedicated right-detail scrollbar distinct from the browser/page scrollbar.
   - Scrolling over the right detail operates on the detail panel instead of dragging the whole page through the long evidence content.

## Layout correction

The result page now receives a dedicated full-width main class instead of relying on a translated oversized canvas. This removes the V3 horizontal-scroll/title-offset issue without changing other application screens.

## Real Weber visual check

Checked at 1536×900 against the real Weber Golden preview:
- title centered in the left workspace;
- no horizontal page scrollbar caused by the result canvas;
- candidate rows remain readable without the V3 compression/wrapping;
- right panel starts directly with evidence images;
- no removed explanatory labels remain;
- independent right-detail scrollbar is visible.

## Verification

- MVP/UI probes: **93/93**
- T003 localization: **15/15**
- T004 evidence object: **16/16**
- T006 OCR: **5/5**
- source acquisition: **106/106**
- Footnote-first: **58/58**

New V4 UI probes protect:
- title placement inside the left workspace;
- independent right-detail scrolling;
- removal of the oversized horizontal canvas transform;
- absence of the four removed normal-user labels;
- printed-page visibility while PDF-sequence explanatory copy is hidden.

No retrieval/ranking/model/provider/OCR architecture change.
No new frontend dependency.
No private source data or screenshots added to Git.

## UNIQUE NEXT

User visually reviews the live Weber V4 page.

Do not merge `ui-result-page-v0` to `main` until accepted or revised.

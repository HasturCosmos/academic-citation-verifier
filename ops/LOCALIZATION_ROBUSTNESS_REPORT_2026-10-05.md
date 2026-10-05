# LOCALIZATION ROBUSTNESS REPORT — 2026-10-05

Status: **COMPLETE / ACCEPTED BY AUTOMATED + REAL-CASE EVIDENCE**
Branch: `localization-robustness-v0`
Base: `main@8abd153`

## 1. Scope held

This fix changed only the evidence-localization layer.

Changed:
- `tools/t003_evidence_localize.py`
- `tools/t003_regression_probes.py`

Not changed:
- semantic retrieval;
- embeddings;
- ranking/reranking;
- query construction;
- chunking;
- k;
- model/provider architecture;
- source acquisition;
- UI;
- Fresh A/B hard-coded knowledge.

## 2. Reuse-first result

The existing T003 locator architecture was retained:
- page-hint window search;
- whole-PDF fallback;
- exact/ambiguous/unmatched/needs_ocr states;
- normalized-to-source mapping;
- cross-page fragments;
- PDF geometry and original-page highlighting.

No new matching framework or dependency was added.

## 3. Fix

The locator normalization now applies Unicode NFKC compatibility folding while preserving traceability.

Examples handled safely:
- CJK compatibility/radical forms;
- full-width forms;
- superscripts;
- compatibility fractions / expanding forms.

Normalization is performed per source character / PDF text entry so every normalized character remains mapped to the original source unit that owns its PDF geometry.

Whitespace and existing invisible-format tolerance remain.

No broad punctuation-deletion or fuzzy page matching was added.

## 4. Focused regression protection

T003 probes expanded from 15 to 18 checks.

New checks:
1. `unicode_nfkc_mapping`
   - compatibility forms normalize as expected;
   - normalized positions map back to original source indices/entries.
2. `unicode_nfkc_pdf_geometry`
   - an ASCII candidate can locate a compatibility-form PDF glyph;
   - highlight geometry remains correct.
3. `unicode_nfkc_expansion_geometry`
   - when one PDF glyph expands into several normalized characters, all normalized positions map back to that one source glyph;
   - highlight stays on the real glyph rather than inventing geometry.

Focused result: **18/18 PASS**.

## 5. Fresh Case A replay

Before fix:
- 13 candidates;
- 0 located;
- 0 highlights;
- product state: `no_corresponding_passage`.

Locator-only replay after fix:
- 5 located;
- relevant human-gold-area candidates include:
  - rank 4 -> PDF p.130;
  - rank 5 -> PDF p.130;
  - rank 9 -> PDF pp.128-129;
- highlight images emitted and visually inspected;
- page/highlight placement is correct.

Full accepted-product rerun after fix:
- product state: **`multiple_candidates`**;
- 13 candidates;
- 5 located;
- 7 highlight images;
- 0 model calls;
- USD 0.00;
- wall time: 64.2 s.

The fix does not recover every plausible passage. In particular, some pp.140-141 material remains unmatched. This is accepted: the Goal required safe localization improvement, not exhaustive fuzzy matching.

## 6. Fresh Case B replay

Before fix:
- 11 candidates;
- 0 located;
- 0 highlights;
- product state: `no_corresponding_passage`.

Locator-only replay after fix:
- rank 9 -> PDF p.110 becomes `located`;
- highlight image emitted and visually inspected;
- the highlight lands on the “主要历史对象 / 次要历史事实 / 价值关系” passage.

Full accepted-product rerun after fix:
- product state: **`evidence_found`**;
- 11 candidates;
- 1 located;
- 1 highlight image;
- PDF p.110;
- 0 model calls;
- USD 0.00;
- wall time: 64.84 s.

Other relevant candidates remain visible as retrieval candidates but are not falsely promoted to page-verified evidence.

## 7. Full regression

Final post-fix suites:

- MVP/UI: **93/93**
- T003: **18/18**
- T004: **16/16**
- T006 OCR: **5/5**
- source acquisition: **106/106**
- Footnote-first: **58/58**

All green.

## 8. Evidence honesty

The fix preserves:
- ambiguous -> ambiguous;
- unmatched -> unmatched;
- needs_ocr -> needs_ocr;
- only defensible unique full matches produce geometry/highlights;
- no page guessing;
- no hard-coded Fresh A/B answer.

## 9. Codex routing note

The planned Codex route was:
- DeepSeek V4.1 Flash;
- Medium reasoning;
- Goal mode.

The local Codex CLI correctly detected `deepseek-flash` but the automation shell did not inherit `DEEPSEEK_API_KEY`.
No credential was read, copied or requested.
Implementation therefore proceeded directly through the authorized local repository tools.

## 10. Verdict

**Localization robustness Goal: PASS.**

This is intentionally a partial robustness fix, not a fuzzy-localization project.
NFKC removes a confirmed real-world failure mode and restores page evidence for both Fresh A and B while keeping all regressions green.

## 11. UNIQUE NEXT

Technical MVP development is no longer the critical path.

Move to **final product / portfolio packaging**:
- freeze the accepted MVP baseline;
- prepare a concise demo path;
- prepare portfolio/README evidence;
- prepare resume-ready project bullets;
- preserve the known limitations honestly.

Do not reopen semantic retrieval unless a later real-user failure demonstrates that it is necessary.

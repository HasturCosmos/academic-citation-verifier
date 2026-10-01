# REUSE_SCAN_2026-10-01

Status: completed research scan; no architecture change authorized by this note.

## Trigger

The user asked whether the project was beginning to reinvent open-source functionality after T004 and requested a new Reuse Scan before further development.

## Current product

**二流文科生的二手文献引用助手**

Core target remains: secondary-literature passage / citation / page -> corresponding Chinese primary-source evidence -> copyable original text + original-page evidence + page + honest citation metadata.

## Closest reusable projects found

### 1. Future-House/paper-qa (PaperQA2)
Already reused in T001-T004 for retrieval. Keep as the current retrieval component until evidence says otherwise.

### 2. docushell/ethos
Very close to the custom T003 evidence-localization layer.
It is a deterministic document evidence / citation-grounding layer with page coordinates, crop descriptors, rendered evidence crops via PDFium, explicit capability limitations, and an `ocr_required` failure for scanned/image-only PDFs.
Apache-2.0. Local/no-network base flow.
Potential reuse: replace or shrink T003's custom pypdfium2/Pillow evidence layer.
Important integration note: no prebuilt Windows CLI artifact; Windows requires building from source, and PDFium is caller-supplied.

### 3. hearthresearch/citefact
Audits manuscript claims against full text of cited sources. It parses citations, resolves bibliography items, converts source PDFs, verifies quotes deterministically, performs optional LLM claim checks, and emits HTML/JSON reports. Uses Docling through its PDF conversion path and can OCR scans.
MIT.
Potential reuse later: claim-vs-source verification, report structure, OCR/Docling integration patterns.
Not a direct replacement for our primary-source discovery workflow because it assumes cited source/bibliography/PDFs are already available.

### 4. markrussinovich/refchecker
Mature reference identity/metadata verifier with Semantic Scholar/OpenAlex/CrossRef/DBLP/ACL Anthology integration, web/desktop/CLI/API surfaces, and large test coverage.
MIT.
Potential reuse later: source identity, metadata validation, bibliographic discovery.
Not a passage-level Chinese-book evidence locator.

### 5. saadyaq/citation-verifier / Prithiv04/SciVerify
Both implement claim-vs-source verification pipelines with evidence retrieval and support/partial/not-supported style verdicts.
Potential reuse later: verdict schemas, claim extraction, source-fetching patterns.
They are focused on cited sources/scientific-paper workflows rather than discovering Chinese primary text behind humanities secondary literature.

### 6. AkariAsai/OpenScholar
Large-scale scientific-literature retrieval and synthesis. Strong retrieval precedent but not a direct fit for page-grounded Chinese primary-source tracing. Its datastore/retriever scale is unnecessary for the MVP.

## Finding

No open-source project found in this scan appears to implement the full target workflow end to end:
secondary humanities passage with fallible clues -> discover corresponding Chinese primary source/edition -> retrieve plausible passages -> return exact original-page visual evidence + copyable citation metadata.

However, individual layers already exist and should be reused rather than rebuilt.

The strongest newly discovered overlap is **Ethos vs T003 evidence localization**. Therefore the project should pause evidence-layer expansion and run a bounded replacement benchmark before writing more custom evidence code.

## Proposed next gate

### T005A — evidence-layer reuse benchmark (proposed, not yet milestone-accepted)

Use the existing C04 artifacts only; do not rerun PaperQA2 and do not spend model/API tokens.

Compare:
- current T003 pypdfium2/Pillow evidence layer;
- Ethos on the same stored candidates / source PDF.

Evaluate:
1. Chinese text localization;
2. exact PDF page;
3. coordinates/crops;
4. cross-page evidence;
5. explicit unmatched/ambiguous/OCR-required behavior;
6. output schema/provenance;
7. Windows integration burden;
8. runtime;
9. dependency/maintenance burden;
10. how much custom T003 code can actually be deleted.

Decision rule:
- adopt Ethos only if it clearly reduces custom code/maintenance without losing current C04 behavior or making Windows/MVP operation materially harder;
- otherwise keep the current thin T003 adapter and record Ethos as a future option.

After T005A, proceed to a new real failure-state case (current TASK_QUEUE priority) using whichever evidence layer wins.

## Guardrail

Do not build custom OCR, claim-verification engines, citation metadata resolvers, or report frameworks before checking Docling/citefact/RefChecker and related maintained projects first.

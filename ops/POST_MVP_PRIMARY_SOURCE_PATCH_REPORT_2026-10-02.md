# POST-MVP PATCH REPORT — primary-source intake — 2026-10-02

Status: COMPLETE — post-MVP pilot patch, executed under
`ops/POST_MVP_PRIMARY_SOURCE_PATCH_GOAL_2026-10-02.md`.

This is **not** a new MVP milestone and does not reopen the accepted MVP (D019).
It fixes the P0 intake blocker found by the first real user run
(`ops/PILOT_FINDING_2026-10-02_PRIMARY_SOURCE_INTAKE.md`) and makes primary-source
PDF upload the normal web path.

## 1. What was broken

`tools/mvp_app.py::_handle_run` built a custom source with `"metadata": ""` whenever
the user typed a local source path and left the metadata field blank.
`tools/mvp_pipeline.py::resolve_paths` then did `Path("")` → repository root, saw it
exist, and tried to `read_text()` a directory → Windows `PermissionError [Errno 13]`
for the user.

The same run used an **EPUB** as the primary source. The evidence contract requires a
stable page geometry plus an original-page image, so an EPUB cannot be final
page-grounded evidence, and the product silently accepted it as an input anyway.

## 2. Fixes in this patch

### P0 — blank metadata and path integrity

- blank / whitespace-only metadata now means **"no metadata"**
  (`resolve_paths` → `metadata_path=None`, `metadata={}`); `Path("")` is never used;
- a metadata path is read only when it **exists and is a regular file**
  (`optional_file_path`), and `load_metadata` turns directory / unreadable /
  invalid-JSON input into a Chinese message instead of a traceback;
- the primary-source path itself is validated (exists, regular file, real `%PDF`
  header) before a job starts;
- `run_job` now catches `SystemExit` as well, so a validation problem inside a worker
  thread can no longer leave a job stuck at "running".

### P1 — primary-source PDF upload is first-class

- the form's ③ is now **"上传一手文献 PDF（推荐）"** with a file picker;
- the uploaded PDF is written only below the git-ignored
  `data/private/mvp_uploads/<timestamp>/primary/` and is carried through the confirm
  step as a hidden `primary_upload` path;
- a `primary_upload` value is accepted only when it resolves inside the configured
  uploads directory, so a form field cannot point a run at an arbitrary local file;
- registered C04 / T005B-01 sources stay available but are labelled
  **"内置示例 · …"** (demo / cached examples);
- the manual local path + metadata JSON moved into an **advanced** collapsible block,
  and the confirm page states which primary source the run will actually use.

### Format policy (before the job starts)

- PDF only: PDFs with a text layer use the accepted text-layer path, image-only PDFs
  use D017 RapidOCR according to the selected OCR mode;
- EPUB is rejected up front with the reason (no fixed pagination, no locatable
  original page image) and an explicit statement that converting an EPUB into page
  numbers would be fabricated evidence;
- other formats (`.docx`, …) get a short "PDF only" message; a renamed non-PDF with
  a `.pdf` suffix is caught by the `%PDF` header check.

## 3. Evidence

Reproduction of the exact pilot input (blank metadata + custom local PDF path) over
the real HTTP surface, using the real C04 text-layer PDF:

```
extract-status 200
extract-has-confirm-page True
extract-traceback False
run-status 200  job web-20261002-214729
job-done True   job-error False
run-source {"source_id": "C04", "label": "自定义本地 PDF：C04.pdf",
            "pdf": "data/private/C04/pqa_corpus/C04.pdf", "metadata": "",
            "docname": "C04"}
result-state multiple_candidates=True   PermissionError in result page: False
```

Before the patch this same input produced
`PermissionError: [Errno 13] Permission denied: '<repo root>'`.

EPUB rejection through the headless entry point:

```
$ .\.venv\Scripts\python.exe tools\mvp_app.py --run-once `
    --secondary-text "韦伯认为支配的正当性类型有三种。" `
    --source-path "D:/books/学术与政治.epub"
EPUB 不能作为核验用的一手文献：它没有固定页码，也没有可定位的原页图像，……（exit 1）
```

Registered demo/cached sources still work through the same entry point (0 model
calls, $0.00):

```
--source C04       state=multiple_candidates route=text_layer cands=5 located=5 imgs=8
--source T005B-01  state=multiple_candidates route=ocr        cands=5 located=5 imgs=7
```

## 4. Tests (all zero-cost, 0 model calls / $0.00)

| Suite | Result |
| --- | --- |
| `tools/mvp_probes.py` | **70/70** (44 before the patch; +26 intake/upload probes) |
| `tools/t003_regression_probes.py` | **15/15** |
| `tools/t004_regression_probes.py` | **16/16** |
| `tools/t006_ocr_probes.py` | **5/5** |

New probes cover: blank and whitespace metadata; a directory passed as the metadata
path; a missing metadata file; EPUB rejection with the pagination explanation; other
unsupported formats; a renamed non-PDF; a directory/missing/blank PDF path; both
registered demo sources still valid; a forged upload path rejected; and a real HTTP
`/extract` → `/run` → `/job` → `/result` round trip with an **uploaded primary PDF**
that ends in `证据已找到` with a highlighted page.

Commands:

```powershell
$env:PQA_HOME = $PWD
.\.venv\Scripts\python.exe tools\mvp_app.py            # web UI, http://127.0.0.1:8765
.\.venv\Scripts\python.exe tools\mvp_probes.py
.\.venv\Scripts\python.exe tools\t003_regression_probes.py
.\.venv\Scripts\python.exe tools\t004_regression_probes.py
.\.venv\Scripts\python.exe tools\t006_ocr_probes.py
```

## 5. Reuse-first result

No new dependency, no framework and no new subsystem:

| Checked | Reused | Gap |
| --- | --- | --- |
| current repo upload/multipart path | `mvp_app.parse_multipart` / `field` / `file_field`, existing `data/private/mvp_uploads/` root | none |
| current pipeline contract | `mvp_pipeline.resolve_paths` / `run_pipeline`, T003/T004 evidence layer, D017 RapidOCR branch | added validation only |
| native/plugin options | not needed: stdlib `http.server` already serves the product surface | none |

Custom code was limited to input validation and one validation helper, because the
existing parser and upload directories already covered the requirement.

## 6. Explicitly not done

- no Z-Library or other unauthorized/pirated download integration;
- no general web/source acquisition subsystem (still a separate Reuse-First + Human
  Gate);
- no paid service, no deployment, no accounts;
- no EPUB-as-evidence conversion; no fabricated page numbers;
- no architecture change and no MVP-milestone reopening.

## 7. Commit

Implementation commit: RECORDED_IN_FOLLOWUP_COMMIT

Working tree after the patch: clean; `git ls-files data/private` empty.

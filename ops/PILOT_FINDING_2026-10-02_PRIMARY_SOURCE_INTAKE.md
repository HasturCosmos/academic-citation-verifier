# POST-MVP PILOT FINDING — 2026-10-02 — first real user run

Status: OPEN; real-use blocker.

## What the user did

The user launched the accepted MVP through the local web UI and attempted a real literature-tracing task.

Secondary passage:
a real passage concerning legitimacy/domination.

Primary-source attempt:
the user selected/entered a local copy of Weber's 《学术与政治》 as an **EPUB** path while leaving the optional metadata JSON field blank.

Observed error:
`PermissionError: [Errno 13] Permission denied: '<repo root>'`

## Root cause verified in code

`tools/mvp_app.py::_handle_run` creates a custom source whenever `source_path` is non-empty and passes the blank metadata field as `"metadata": ""`.

`tools/mvp_pipeline.py::resolve_paths` then executes:

- `Path("")` -> current directory;
- resolves that relative path under `REPO_ROOT`;
- `metadata_path.exists()` is true because the repository directory exists;
- `load_metadata(metadata_path)` tries to `read_text()` from the directory;
- Windows raises `PermissionError [Errno 13]`.

This is a real product bug, not user error.

## Second finding: primary-source intake UX is wrong for real use

The accepted MVP surface makes pre-registered C04/T005B cases prominent and exposes an advanced local-path textbox. In real use the user expects a primary source to be either:

1. uploaded/provided directly by the user; or
2. acquired through an available lawful source adapter when the user does not already have the source.

The current UI does not provide first-class primary-source upload.

The user supplied an EPUB. The evidence contract requires stable page provenance and original-page highlighting, so an EPUB cannot by itself serve as final page-grounded citation evidence. It may be useful for discovery later, but the current evidence path should require a PDF/page-image source for final evidence.

## Required immediate patch (no new architecture)

P0:
- blank metadata path must mean "no metadata supplied", never repository root;
- metadata path must be a real file before reading;
- custom source validation must surface a friendly error rather than a traceback;
- unsupported primary-source formats (including EPUB) must be rejected clearly before the pipeline starts.

P1:
- make **Upload primary-source PDF** the normal user path;
- keep the source registry only as demo/cached local examples;
- keep manual local path as an advanced fallback;
- preserve current PDF/OCR evidence contract.

## Separate Human Gate — source acquisition

Automatic acquisition when the user lacks a PDF is a new source-adapter subsystem and must go through Reuse First + a Human Gate.

Do not implement automated download from unauthorized/pirated repositories. The product may later search/connect to lawful/open/authorized full-text sources and otherwise ask the user to upload a legally obtained PDF.

## Acceptance

The post-MVP patch is complete only when:
- blank metadata no longer crashes;
- user can upload a primary PDF from the web UI;
- an EPUB gets a clear explanation that it cannot provide stable page-grounded evidence;
- C04/T005B registered demos still work;
- regressions remain green.

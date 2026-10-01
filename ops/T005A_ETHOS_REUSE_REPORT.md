# T005A — Evidence-layer reuse benchmark report

Status: COMPLETE — **KEEP_CURRENT**. This is a reuse-gate task result, not a
durable architecture decision and not M1 acceptance. Both remain user decisions.

## Examined revision

- Project: `docushell/ethos`, license Apache-2.0 (`LICENSE`, 11357 bytes).
- Default branch `main` at commit `1101f0b6b06557b144769ed82a6ebaa9afb34127`
  (2026-09-07, "Close out the v0.6.0 publication", tree `1d89c0a9…`). This is
  the v0.6.0 publication closeout commit.
- Latest release `v0.6.0`, published 2026-09-07, 16 assets.

Sources read (read-only, via the GitHub connector): repository metadata;
`README.md`; `docs/execution-status.md`; `docs/CLAIMS.md`; `schemas/README.md`;
`pyproject.toml`; `rust-toolchain.toml`; the v0.6.0 release manifest, asset
list, and body; `docs/validation/v0-6-0-release-closeout-summary.md`;
`python/` and `bindings/` listings.

Cost and side effects: zero model/API calls, $0.00, no dependency installed, no
install attempt, no upstream checkout, no modification to private source
material. The only private-path access was a directory listing to confirm the
existing C04 artifacts are present.

## Decision

**KEEP_CURRENT.** Keep the thin T003 pypdfium2/Pillow adapter.

Ethos overlaps our evidence layer conceptually — it is a deterministic document
evidence/citation-grounding layer with coordinates, crop descriptors, and an
explicit `ocr_required` failure — but it cannot be exercised on this machine
without installing a Rust toolchain, and even with one it would not delete any
current T003 code without losing behavior the product depends on. Record Ethos
as a future option.

## Phase 1 — static feasibility audit

| # | Required question | Finding | Evidence |
| --- | --- | --- | --- |
| 1 | Exact license and integration surface | Apache-2.0. Published surfaces: Rust crates `ethos-doc-core` / `ethos-verify` / `ethos-pdf`; Python wheel `ethos-pdf`; npm `@docushell/ethos-pdf`; macOS arm64 + Linux x64 CLI archives | `LICENSE`; `README.md` package table; `docs/execution-status.md` generated release block |
| 2 | Windows-runnable path without a new system-wide toolchain | **No.** v0.6.0 assets are macOS arm64 + Linux x64 only. Ethos's own closeout states the run "produced a verify-only Windows candidate, which was deliberately withheld because Windows packaged artifacts remain a blocked lane". npm "fails before invoking a binary" on unsupported platforms | v0.6.0 release asset list; `docs/validation/v0-6-0-release-closeout-summary.md`; `README.md` "Windows CLI artifact — Build from source on Windows" |
| 3 | Python integration still requires an external Ethos CLI | **Yes.** The wheel is a thin wrapper: `EthosCli(binary="/path/to/ethos")`. "The Python wheel does not bundle the CLI or PDFium." | `pyproject.toml`; `python/README.md`; `bindings/python/` contains only a 129-byte README |
| 4 | Caller-supplied PDFium required | **Yes** for PDFium-backed commands, via `ETHOS_PDFIUM_LIBRARY_PATH`. Satisfiable locally: `.venv/Lib/site-packages/pypdfium2_raw/pdfium.dll` (7,260,672 bytes) exists. Not the binding constraint | `README.md`; `docs/execution-status.md`; local environment check |
| 5 | Output exposes page coordinates/crops sufficient for our original-page evidence UI | **Partially.** Crop descriptors and rendered crops exist (`ethos crop_element`, `verify --crop-dir`). Canonical geometry is integer quanta, and Ethos's determinism contract states exact page boxes and rendered images "may differ between platforms and are not part of that guarantee" | `schemas/README.md`; `README.md` determinism section; `docs/CLAIMS.md` |
| 6 | Cross-page evidence and explicit OCR-required behavior supported | OCR-required **yes** (`ocr_required`, fails closed, never guesses) — this matches our `needs_ocr`. Cross-page **no, in our sense**: v0.6.0's adjacent-element join infers continuity from geometry and then gates `semantic_unverified` **false**; it is not "one candidate passage split into one fragment per page" | `README.md`; v0.6.0 release body |
| 7 | What Ethos does NOT do | No semantic matching (literal matching after a pinned normalization profile; a paraphrase is explicitly *not* grounded). No OCR. No judgement of truth/relevance/completeness. No passage *discovery* — it consumes a pre-existing document representation plus citations | `docs/CLAIMS.md` §§1-2; `README.md` FAQ |

### Phase 2 blocking finding (guardrail)

Local environment (checked before any install):

- `rustc`, `cargo`, `rustup` — **not present**;
- `make` — **not present**;
- `wsl` present but **no distribution installed** (`wsl --list --verbose` exits 1);
- `node` / `npm` present, but the npm package vendors only macOS/Linux binaries.

Source-checkout prerequisites are Rust via `rustup` (pinned `1.87.0` in
`rust-toolchain.toml`), `make`, and Python 3. Every Windows-runnable path
therefore starts with installing a Rust toolchain.

The T005A brief requires stopping before exactly this: "If a clean isolated
Windows run requires installing a system-wide Rust toolchain or materially
expanding the environment, STOP before installation and record that integration
burden", and "no system-wide dependency installation solely to make Ethos work".

**Phase 2 was therefore not run.** It is not the "cheap" case the brief
conditions it on, and running it would require the environment expansion the
brief forbids without explicit user authorization. This is a deliberate,
brief-mandated stop, not an oversight.

## Capability comparison against T003

T003 = `tools/t003_evidence_localize.py` (847 lines) + `tools/t003_regression_probes.py`.

| Capability | T003 | Ethos | Verdict |
| --- | --- | --- | --- |
| Fallible page hint → bounded window → whole-PDF fallback | `locate()` (lines 296-395) | Not a feature. A locator must resolve; 0.6.0 only added *searching the cited page before judging* a page-only locator | T003 unique |
| `located` / `ambiguous` / `unmatched` | Explicit three-state outcome; only a unique full match may emit a highlight | Label set is `grounded` / `stale` / `missing` / `mismatched` / `unsupported` / `capability_blocked`; repeated text elsewhere does not by itself produce an ambiguity verdict | T003 unique |
| `needs_ocr` | `MIN_TEXT_LAYER_CHARS` + status | `ocr_required` | Equivalent — already matched |
| Cross-page candidate → one fragment per page | `_map_span` + `_build_fragment` (lines 348-497) | Adjacent-element join, gated closed via `semantic_unverified` | T003 unique |
| Per-character boxes in the renderer's own transform | `_charbox` + `_to_device` via `FPDF_PageToDevice` with the same args as `FPDF_RenderPageBitmap` (lines 138-157, 409-441) | Element-scoped / quantized boxes; cross-platform box stability explicitly not guaranteed | T003 unique for pixel-exact highlighting |
| Per-line highlight runs (never one rectangle over body text) | `group_runs` (lines 503-553) | Element crops, not run-level highlights | T003 unique |
| Page render + highlight overlay + ink/geometry sanity | `draw_highlights`, `ink_ratio`, `finalize_fragment` (lines 555-646) | Renders element crops (PDFium-backed) | T003 unique |
| Source-integrity fingerprints | sha256 of PDF + results JSON | sha256 subject digest inside an in-toto statement, plus `attestation` | Ethos is stronger; not needed at this stage |
| Deterministic, offline, zero-API | Yes | Yes, byte-for-byte | Compatible |

## Exact T003/T004 surface: removed vs retained

- **Removed: nothing.** No file, function, or line is deleted by this task.
- **Retained in full:** `tools/t003_evidence_localize.py` (847 lines) and
  `tools/t003_regression_probes.py`. The only sub-surface Ethos could in
  principle have displaced is `draw_highlights` + `group_runs` + the status
  vocabulary — and it would replace them with a coarser primitive (whole element
  crop), a second document representation (`ethos.json`), and a CLI subprocess,
  while still not covering cross-page fragments or the ambiguity rule.
- `tools/t004_backend_slice.py` and `tools/t004_regression_probes.py` are
  untouched and reference no Ethos surface.

## Dependency / runtime implications

Adopting Ethos today would add, not remove:

- a Rust 1.87.0 toolchain and `make`;
- a source checkout plus `cargo build --locked -p ethos-cli` (or a Linux runner);
- `ETHOS_PDFIUM_LIBRARY_PATH` wiring;
- a subprocess boundary and a parallel `ethos.json` document representation;
- an in-toto Statement unwrapping step in every consumer (the 0.6.0 breaking change).

It would **not** remove pypdfium2 or Pillow. The net effect is a materially
larger environment for the same product behavior — the opposite of the reuse
gate's purpose.

## Regression expectations

None change. This task altered no behavior and no dependency, so T003's 15/15
and T004's 16/16 probe results and the C04 acceptance evidence stand as recorded.

## Reusable non-code assets (recorded for the future, not adopted now)

- `schemas/normalization-vectors.json` and
  `schemas/normalization-vectors-unicode-compat-v1.json` (Apache-2.0): executable
  input/output vectors pinning their normalization profiles. Useful as a
  conformance reference if our whitespace + invisible-character normalization
  ever needs an external spec. Our profile is deliberately narrower (it keeps an
  index map back to original character positions because geometry depends on it),
  so this is reference material, not a drop-in.
- The `capability_limits` / explicit-limitation vocabulary, and the
  `semantic_unverified` "fail closed rather than guess" pattern, are worth
  remembering when the product presents honest uncertainty in a UI.

Nothing is vendored by this task.

## When to re-open this decision

Any one of:

1. Ethos publishes an official Windows CLI artifact or a packaged native Python
   binding (Windows packaged artifacts are an explicitly blocked lane today);
2. the product needs claim-vs-source verification over *already-parsed*
   documents rather than passage localization — the `citefact` / `refchecker`
   lane already parked in the backlog, where Ethos's verification-report and
   proof-statement model is a genuine fit;
3. Ethos gains explicit ambiguity and cross-page-passage semantics.

## Boundary

This report settles one component question for one candidate project. It is not
a durable architecture decision, not M1 acceptance, and not a general reuse
scan. `citefact`, `refchecker`, `SciVerify`, and `OpenScholar` were not evaluated
here; they stay on the backlog with their original scoping.

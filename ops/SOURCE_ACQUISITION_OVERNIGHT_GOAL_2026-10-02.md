# POST-MVP OVERNIGHT GOAL — lawful source acquisition Phase 1 — 2026-10-02

Status: AUTHORIZED FOR LONG-RUN EXECUTION.

## Mission

Extend the accepted MVP only in one bounded direction:

**When the user does not already have a primary-source PDF, help discover and acquire a lawful/open/authorized full-text PDF when one is genuinely available; otherwise return an honest "upload your legally obtained PDF" result.**

This is a post-MVP source-acquisition Phase 1. It is NOT permission to integrate unauthorized/pirated repositories or to weaken the page-grounded evidence contract.

## Product boundary

Accepted evidence still requires stable page provenance and original-page images.

Therefore:
- a directly downloadable/open PDF may become a searchable primary-source resource;
- metadata-only records, previews, snippets, EPUB-only resources, or borrow-restricted/non-downloadable items are discovery hints only, never final page-grounded evidence;
- never fabricate page numbers or treat a preview/snippet as the source text;
- never bypass paywalls, DRM, login restrictions, borrowing restrictions, robots/terms, or access controls.

## Before coding — Reuse First

Read:
- AGENTS.md
- ops/PROJECT_STATE.md
- ops/TASK_QUEUE.md
- ops/DECISIONS.md
- ops/PRODUCT_V0_1.md
- ops/PILOT_FINDING_2026-10-02_PRIMARY_SOURCE_INTAKE.md

Then run a bounded current-source scan focused on maintained lawful/open discovery/full-text routes.

At minimum verify official docs/current behavior for:
1. Google Books API — search + accessInfo/publicDomain/pdf availability/download link;
2. DOAB / OAPEN REST APIs — open-access books, metadata, bitstreams/full-text links;
3. OpenAlex — scholarly metadata and OA locations, especially articles/chapters rather than assuming book coverage;
4. Unpaywall only where DOI-based OA resolution is still appropriate; note that its free-text search endpoint was retired in Sep 2026 and OpenAlex is the successor;
5. Internet Archive only for clearly public-domain/open-download items; do NOT automate borrow-restricted/copyright-limited acquisition;
6. other maintained lawful/open sources only if they materially improve Chinese/humanities coverage.

Record:
- query capability;
- full-text/PDF capability;
- license/access signal;
- whether automated download is clearly permitted;
- API key/account requirement;
- likely usefulness for Chinese humanities books;
- integration burden;
- why each candidate is adopted, deferred, or rejected.

Do not turn this into open-ended ecosystem research.

## Phase A — define one thin source-finder contract

Create one small internal result schema such as:
- source_provider
- title
- authors
- year
- identifiers
- access_status
- license
- landing_url
- pdf_url (only if genuinely open/directly usable)
- evidence_eligible (boolean)
- reason_not_evidence_eligible

Distinguish:
- OPEN_PDF_AVAILABLE
- OPEN_PAGE_SOURCE_AVAILABLE
- METADATA_OR_PREVIEW_ONLY
- USER_UPLOAD_REQUIRED
- ERROR / RATE_LIMIT

Do not silently treat all URLs as PDFs.

## Phase B — implement only the smallest useful adapters

Prefer 1–3 high-value adapters over many shallow integrations.

Priority:
1. open-access book route with actual PDF/full-text links (DOAB/OAPEN is a strong candidate);
2. Google Books for bibliographic/discovery/access-state information and public-domain PDF when actually available;
3. scholarly OA article/chapter resolution through OpenAlex/Unpaywall only if it fits the product and can yield a stable PDF.

Adapters must:
- use official/public interfaces;
- require no paid service;
- require no account/API key unless there is a clear free documented route already available;
- validate content type / PDF header before saving;
- save downloads only under git-ignored data/private/;
- persist provenance and provider/license/access metadata;
- never auto-download ambiguous/restricted content.

## Phase C — product-surface prototype

Add a reversible, clearly labelled route to the local MVP:

If user has no primary PDF:
- allow a simple search such as title/author/ISBN/DOI;
- show discovered candidates with provider + access status;
- if a clearly open PDF exists, allow/use the lawful download;
- if only metadata/preview exists, say it cannot be used as page-grounded evidence and ask for user upload;
- do NOT hide the current "upload primary PDF" path.

Keep the existing uploaded-PDF path as primary/reliable.

No visual polish.

## Phase D — real benchmark cases

Use at least:
1. one known open/public-domain book where a lawful PDF should be obtainable through an adapter;
2. one scholarly OA article/chapter if a suitable adapter was implemented;
3. one closed/non-downloadable book case showing honest USER_UPLOAD_REQUIRED.

Do not use the user's copyrighted private sources as web-download targets.

Measure:
- discovery success;
- whether a real PDF is obtained;
- PDF validity;
- whether the downloaded PDF can enter the existing pipeline;
- provenance retained;
- false-positive/preview-only handling;
- time/network calls;
- cost.

If provider behavior/terms are unclear, stop that provider and record DEFERRED rather than guessing.

## Phase E — integration and regression

Only if a provider produced a valid open PDF:
- feed it through the existing canonical pipeline;
- preserve T003/T004 evidence rules;
- do not fork the evidence layer;
- keep the existing primary upload route unchanged.

Run:
- mvp_probes
- T003
- T004
- T006
- new source-acquisition probes

No paid model/API calls.

## Phase F — report and morning handoff

Create:
- ops/SOURCE_ACQUISITION_REUSE_SCAN_2026-10-03.md
- ops/SOURCE_ACQUISITION_PHASE1_REPORT_2026-10-03.md

Report:
- providers checked;
- exact official interfaces;
- exact access/legal boundary;
- adapters implemented;
- benchmark evidence;
- whether a lawful open PDF actually entered the evidence pipeline;
- failures / rate limits;
- all commits;
- launch/use instructions;
- one recommended NEXT.

## Human Gates / stop rules

Continue through ordinary bugs, tests, refactors and provider-specific reversible details.

STOP only if any of these is required:
- paid service/subscription;
- API key/account or new credential;
- login/session borrowing;
- bypassing paywall/DRM/access control;
- unauthorized/pirated repository integration;
- broad/durable architecture change beyond a thin optional source-finder;
- privacy-sensitive upload to an external service;
- unclear terms where automated download may not be allowed.

If all candidate providers are unsuitable, finish with a high-quality reuse report and USER_UPLOAD_REQUIRED design. That is a valid Phase 1 result.

## End state

At the end:
- push origin/main;
- leave tree clean;
- update PROJECT_STATE / TASK_QUEUE / RUN_LOG / AGENTS;
- do not reopen MVP completion;
- do not ask the user for routine intermediate confirmation.

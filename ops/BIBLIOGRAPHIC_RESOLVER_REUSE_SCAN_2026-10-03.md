# Reuse-First — Chinese book bibliographic resolver — 2026-10-03

Status: EVALUATED / HUMAN GATE. No provider, credential, dependency or architecture has been added.

## Trigger

Pilot Case 001 now passes the source-resolution safety gate but the same real citation still cannot resolve a trustworthy Chinese edition. The safe build correctly returns `USER_UPLOAD_REQUIRED` instead of offering unrelated PDFs.

The next product gap is therefore **bibliographic edition resolution**, not evidence retrieval and not unrestricted source acquisition.

## Product separation

Keep these as two different jobs:

1. **Bibliographic resolver** — identify the likely cited edition (title, author, translator, publisher, year, ISBN, provenance/conflicts).
2. **Evidence acquisition** — obtain a lawful matching PDF or ask the user to upload it, then run the already accepted evidence/highlight pipeline.

A metadata record may establish an edition lead without being evidence and without being downloadable.

## Reuse scan

### 1. Current repository

Reuse:
- existing Footnote-first identity model and provenance/conflict handling;
- existing Google Books adapter;
- existing D024 relevance/actionability gate;
- existing owned-PDF upload and evidence pipeline.

Gap:
- the finder currently treats providers mainly as acquisition sources; it lacks a first-class metadata-only edition resolver;
- Google Books anonymous requests are quota/rate-limit unreliable in the current run;
- the current exact-identifier path should receive an end-to-end probe before resolver rollout because `match_score()` scores title/author/year terms, while ISBN/DOI may be the only confirmed handle.

### 2. ChatGPT / Work / native web

Useful for research and manual control-room verification, but not a deterministic product backend. Do not make the MVP depend on ChatGPT web search for edition identity.

### 3. Skills / Plugins / MCP

Plugin discovery for Google Books / Open Library / WorldCat / ISBN bibliographic lookup returned no suitable catalog resolver. GitHub is already the project state bus.

### 4. Installable plugin

No suitable plugin found. Do not install unrelated research/read-later plugins.

### 5. GitHub / open source

- `internetarchive/openlibrary-client` exists as an official/reference Python client for Open Library.
- For this project it is unnecessary overhead: Open Library exposes simple public REST/JSON endpoints, and the current code already has a small stdlib HTTP adapter pattern.
- Google Books has official API clients/discovery descriptions, but the repository already has a Google Books adapter. Prefer adapting it over adding another dependency.

Decision preference remains: direct reuse > small adaptation > new subsystem.

### 6. Official services

#### Google Books — RECOMMENDED first resolver

Official public-data API supports book search and fielded queries such as `intitle:`, `inauthor:`, `inpublisher:`, and `isbn:`. Public-data requests use an application identifier such as an API key; OAuth is not required for public volume data.

Pilot evidence is unusually strong: Google Books publicly has the exact 1998 edition:
- title: 学术与政治：韦伯的两篇演说
- translator: 冯克利
- publisher: 生活·读书·新知三联书店
- year: 1998
- ISBN: 7108011956 / 9787108011954

This directly addresses the current real failure. The existing adapter means implementation would be a bounded adaptation rather than a new provider architecture.

Human Gate: creating/providing an API key (credential).

Official docs:
- https://developers.google.com/books/docs/v1/using
- https://developers.google.com/books/docs/v1/reference/volumes/list

Exact public record:
- https://books.google.com/books?id=UqGgAAAACAAJ

#### Open Library — RECOMMENDED no-key fallback, not primary

Open Library provides public low-volume APIs, work/edition separation, edition metadata, ISBN lookup, and search results that can include edition-level fields. It is well aligned with this product and can be called without a per-user API key.

However, quick checks have not established reliable coverage of the exact 1998 Chinese edition. Use it as a supplementary resolver, not as the only resolver.

Official docs:
- https://openlibrary.org/dev/docs/api/search
- https://openlibrary.org/dev/docs/api/books
- https://openlibrary.org/developers/api

#### CALIS — valuable Chinese catalog, defer programmatic integration

CALIS' union catalog is highly relevant to Chinese editions and its public site reports millions of union-catalog records. CALIS also documents an OpenAPI mechanism, but external applications require institutional ClientKey/ClientSecret authorization; catalog services and data download are institution/member-governed.

Use the public OPAC as a human verification route if needed. Do not make CALIS API integration the first MVP resolver unless institutional access is explicitly authorized.

Sources:
- https://smart.calis.edu.cn/
- https://project.calis.edu.cn/
- https://ill.calis.edu.cn/pages/help.html

#### WorldCat — reject for MVP

WorldCat Search API 2.0 is a strong bibliographic source, but OCLC states that production access requires qualifying library subscriptions and OAuth/WSKey access. This is disproportionate for the current MVP.

Official:
- https://www.oclc.org/developer/api/oclc-apis/worldcat-search-api.en.html

#### National Library union catalog / OLCC — reject as first integration

The National Library union-catalog service exposes professional Z39.50/member data services and documents per-record charges for some bibliographic data delivery. It is not a zero-friction public JSON resolver for this MVP.

Official:
- https://olcc.nlc.cn/page/service.html

## Recommended product route

**A. Google Books keyed metadata resolver first.**
- Metadata only; do not imply that a Google Books record is evidence or downloadable full text.
- Search the confirmed Footnote-first identity using title + translator/year, then fielded title/author/publisher/ISBN variants within a small bounded query budget.
- Return edition candidates with provenance and conflicts.
- Reuse the existing D024 safety gate.
- After user/logic confirms an edition, hand off to the existing lawful-PDF acquisition/upload path.

**B. Open Library as a no-key fallback.**
- Edition-aware metadata only.
- Same normalized candidate schema and safety gate.

Do not add WorldCat/CALIS credentials or scraping in this stage.

## Required pre-implementation acceptance addition

Before/with resolver implementation, add an end-to-end identifier probe:
- an ISBN/DOI-only identity that retrieves a record carrying the same identifier must not be rejected merely because lexical `match_score()` over title/author/year is low;
- exact identifiers remain strict; no fuzzy identifier matching.

## Human Gate

Recommended decision: authorize creation/use of a **Google Books API key for public bibliographic metadata only**, while keeping Open Library as the no-key fallback.

This requires user approval because it introduces a credential. No code should add/store the key before approval.

# Antigravity Project Tracker

This tracker acts as the central command list for your Antigravity 2.0 Agents. Check off items as agents construct, test, and verify the pipeline components in parallel.

## 🚀 1. Infrastructure Scaffolding
- [x] Create `docker-compose.yml` defining FastAPI, RabbitMQ, Celery, Redis, and Postgres.
- [x] Write `Dockerfile` for api-service and celery-worker containers.
- [x] Write `nginx.conf` for reverse proxy (required by docker-compose api-gateway service).
- [x] Write `requirements.txt` with all project dependencies.
- [x] Implement API Gateway entry points in `main.py` with rate-limiting, JWT stub, `/health`, `/ingest`, `/status`, `/hitl`.
- [x] Configure PostgreSQL schema migrations via `models.py` `init_db()` called on startup.
- [x] Connect distributed locks to Redis to prevent concurrent scrapes of identical domains.

## 🔍 2. Crawler & Ingestion Subsystems
- [x] Implement targeted `httpx` scraper restricted strictly to official manufacturer domains (`MANUFACTURER_DOMAINS` map + `BLOCKED_DOMAINS` guard).
- [x] Write fallback parser targeting Grainger (trusted industrial distributor — never retail).
- [x] `MOCK_MODE` env flag for CI/test — returns fixture HTML without hitting live sites.
- [x] Code programmatic PDF spec-sheet downloader + text extractor (`pypdf` with raw-byte regex fallback — no new required dep).
- [x] PDF fallback: regex scan of raw bytes for plain-text spec lines (no pypdf install needed for CI).

## 🏷️ 3. Classification & Attribute Extraction
- [x] Implement `split_value_uom()` — stdlib `re` only, covers "120 V", "50-1/4 in", "47 dBA", fractions, no UOM. Self-asserted.
- [x] Implement `classify_taxonomy()` — keyword-scan fallback with `ponytail:` upgrade comment for bi-encoder.
- [x] Implement `extract_attributes()` — BeautifulSoup CSS selector, drives via `split_value_uom()`.
- [x] Map extracted strings to category LOVs — `validate_lov()` flags unknown values, marks confidence=0.3, routes to HITL (rules.md §2.2). Self-asserted.
- [ ] Deploy semantic vector matcher using HuggingFace / Gemini Embeddings against the 14,000 leaf-level taxonomy. *(Phase 3 — requires embedding model)*

## ✍️ 4. Description Synthesis & Media Assembly
- [x] Implement `synthesize_descriptions()` — deterministic string formatters, all 5 channels, character limits enforced per `rules.md`.
  - [x] SHORT_DESC: 50 chars
  - [x] LONG_DESC1: 250 chars, prose with key specs
  - [x] MOBILE_DESC: 30 chars
  - [x] INVOICE_DESC: 100 chars, CAPS
  - [x] RETAIL_DESC: 150 chars
- [x] Extract verbatim marketing descriptions — `extract_marketing()` returns prose + up to 50 feature bullets, stored as `Feature_N` attributes.
- [x] Build multi-modal asset extractor — `fetch_product_images()` downloads up to 4 images to `IMAGE_STORE` (defaults to `/tmp`; env-var swap for S3/GCS).

## 🛡️ 5. Validation & Quality Gates
- [x] Implement `save_enriched_product()` logic inlined into task — atomic write of attributes + descriptions + bullets + LOV flags in one DB transaction.
- [x] HITL routing — `_route_to_hitl()` inserts to `hitl_queue`; `/hitl` POST route for manual review resolution.
- [x] Build `hitl_queue` table for exception routing.
- [x] Implement `validate_mandatory()` — quality gate enforcing zero empty/null values on mandatory attributes and descriptions before any DB write. Self-asserted.
- [ ] Complete full-scale, end-to-end performance run on the 1,000 product input dataset. *(Requires Docker stack + live data)*


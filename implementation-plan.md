# Implementation Plan and Milestones

## 1. Project Phase Rollout

This project is divided into four main execution phases, aligning directly with the core engineering challenges of industrial data scraping, semantic classification, unit parsing, and validation.

```
       [ PHASE 1: Core Scaffolding & Edge Ingress ]
                            │
                            ▼
     [ PHASE 2: Autonomous Crawler & Extraction Engine ]
                            │
                            ▼
         [ PHASE 3: Normalization & Narrative Synthesis ]
                            │
                            ▼
       [ PHASE 4: Traceability, Verification & HITL ]
```

---

## 2. Phase Breakdowns

### Phase 1: Core Scaffolding & Edge Ingress (Week 1)
* **Goal:** Set up local running environments and baseline API pathways.
* **Key Tasks:**
  1. Boot the Antigravity 2.0 workspace and initialize parallel local agents.
  2. Implement the FastAPI API gateway with dynamic token-bucket rate-limiting.
  3. Deploy the Celery worker task runner and link PostgreSQL and the Redis cluster.
  4. Write unit tests for basic connection health.

### Phase 2: Autonomous Crawler & Extraction Engine (Week 2)
* **Goal:** Create robust, safe crawling subsystems and high-precision extraction models.
* **Key Tasks:**
  1. Write the targeted crawler restricted strictly to official manufacturer domains.
  2. Implement fallback crawlers to query trusted industrial distributors (never retail).
  3. Integrate PDF parsing (using `pdftotext` / `pypdf`) to extract technical manual telemetry.
  4. Train/tune a semantic vector search bi-encoder to map input titles into the **14,000 leaf-level categories**.

### Phase 3: Normalization & Narrative Synthesis (Week 3)
* **Goal:** Standardize extracted attributes, split units of measure, and format descriptions.
* **Key Tasks:**
  1. Implement a rule engine that splits raw attribute values (e.g. "120 V" -> Value: `120`, UOM: `V`).
  2. Map all extracted variables to official Lists of Values (LOV), writing automatic flag logic for "new found values".
  3. Code the programmatic description generators for Mobile, Invoice, Short, Long, and Retail formats under rigid character and prefix boundaries.
  4. Ensure raw marketing descriptions are captured verbatim without alterations.

### Phase 4: Traceability, Verification & HITL (Week 4)
* **Goal:** Build the validation loop, audit logs, and Human-in-the-Loop exception dashboard.
* **Key Tasks:**
  1. Implement the database persistence layers for the product attribute triples.
  2. Write verification logic linking each attribute cell to its respective source verification URL (`Ref URL`).
  3. Build the exception handling dashboard that isolates failed scrapes or low-confidence extractions to the DLQ.
  4. Conduct end-to-end performance test sweeps of the full 1,000 product input CSV.

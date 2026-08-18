# Autonomous AI Product Data Enrichment & Taxonomy Pipeline

An enterprise-grade, distributed pipeline designed for **industrial commerce & B2B catalog enrichment**. It autonomously transforms sparse SKU inputs (Part #, Brand, Manufacturer) into verified technical attributes, hierarchical taxonomy classifications, and 5-channel syndicated descriptions with zero cross-SKU contamination.

![Dashboard Preview](screenshot_1_dashboard.png)

---

## 🌟 Key Capabilities & Architectural Highlights

1. **Strict SKU Context Isolation (`ProductContext`)**
   - Cryptographically isolated, request-scoped contexts guarantee **0% cross-SKU data leakage**. A dishwasher will never receive abrasive disc specifications, and vice-versa.
2. **7-Tier Source Quality Hierarchy & Provenance**
   - Calibrated confidence scoring ranging from **Level 1 (Manufacturer PDF)** to **Level 6 (Category Standard)** and **Level 7 (AI Inference)**.
   - Every attribute stores full source provenance (`source_url`, `source_level`, `verification_status`).
3. **Atomic Spec Normalization & LOV Cleaning**
   - Automatically atomizes compound marketing strings (e.g. `33-7/16 in H x 23-7/8 in W x 22-5/8 in D`) into discrete, normalized numeric specifications (`Height: 33-7/16 in`, `Width: 23-7/8 in`, `Depth: 22-5/8 in`).
   - Separates feature highlights (e.g. *CleanBoost*, *3rd Rack*) and certifications (*ENERGY STAR, UL Listed*) from technical specs.
4. **Deterministic 5-Channel Copywriting Engine**
   - Programmatically enforces character limits across e-commerce syndication channels:
     - **Short Desc** ($\le 50$ chars)
     - **Long Desc** ($\le 250$ chars)
     - **Mobile Desc** ($\le 30$ chars)
     - **Invoice Desc** ($\le 100$ chars, CAPS-only)
     - **Retail Desc** ($\le 150$ chars)
5. **Human-in-the-Loop (HITL) Safety Net**
   - Products with missing or conflicting specs are routed to a human review queue with clear reasoning instead of hallucinating fake numbers (`Technical Specs → UNKNOWN`).
6. **High-Throughput Distributed Microservices**
   - Async ingestion via **FastAPI**, distributed background task queue via **Celery & Redis**, and relational storage in **PostgreSQL 16**.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│       Web Dashboard (HTML5 / Vanilla CSS / JavaScript)      │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST API
┌──────────────────────────────▼──────────────────────────────┐
│       API Gateway & Ingestion Service (FastAPI / Nginx)     │
└──────────────────────────────┬──────────────────────────────┘
                               │ Async Task Queue
┌──────────────────────────────▼──────────────────────────────┐
│          Distributed Worker Cluster (Celery + Redis)         │
│   • Multi-Source Discovery & PDF Spec Retrieval             │
│   • Semantic Attribute Classifier & UOM Map                 │
│   • 5-Channel Syndicated Copywriter Engine                  │
│   • Multi-Stage Quality Gate & Contamination Detector       │
└──────────────────────────────┬──────────────────────────────┘
                               │ Clean Enriched Data
┌──────────────────────────────▼──────────────────────────────┐
│           Relational Database (PostgreSQL 16)               │
│   • products • product_attributes • product_descriptions    │
│   • hitl_queue • taxonomy_categories                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24+)
- [Docker Compose](https://docs.docker.com/compose/)

### 1. Clone & Start the Cluster

```bash
git clone <your-repo-url>
cd project-unilog

# Spin up all 6 microservices in detached mode
docker compose up -d
```

### 2. Access the Application

- **Web Dashboard:** [http://localhost:8080](http://localhost:8080)
- **FastAPI Interactive Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Endpoint:** [http://localhost:8080/health](http://localhost:8080/health)

---

## 🧪 Testing & Quality Assurance

Run the automated regression test suite to verify SKU isolation and zero cross-contamination:

```bash
python3 test_product_isolation.py
```

### Test Suite Coverage:
- `test_01`: Sequential processing isolation (Frigidaire Dishwasher $\rightarrow$ 3M Sanding Disc)
- `test_02`: Reverse order processing isolation (3M Sanding Disc $\rightarrow$ Frigidaire Dishwasher)
- `test_03`: Independent search queries and cache keys
- `test_04`: Cross-SKU contamination detection & rejection
- `test_05`: Atomic spec parsing & compound dimension splitting
- `test_06`: Idempotent processing & duplicate attribute prevention
- `test_07`: Marketing copy vs. technical specification separation
- `test_08`: 7-tier source quality levels & confidence verification
- `test_09`: Conflict handling & HITL review triggering
- `test_10`: Diablo Sanding Belt isolation & unsupported claim prevention

---

## 📁 Repository Structure

```
├── Dockerfile                  # Python 3.11 container image
├── docker-compose.yml          # Multi-container orchestration (API, Celery, Redis, Postgres, Nginx, RabbitMQ)
├── main.py                     # FastAPI gateway, routes & Redis caching
├── tasks.py                    # Celery asynchronous worker tasks
├── context.py                  # Isolated request-scoped ProductContext
├── discovery.py                # Multi-source scraper & spec extractor
├── attribute_classifier.py     # Semantic classifier (Specs vs Features vs Certs)
├── normalizer.py               # Unit of Measure (UOM) normalization & regex engine
├── deduplicator.py             # Hierarchy-aware attribute deduplication
├── taxonomy.py                 # Hierarchical taxonomy classification engine
├── copywriter.py               # 5-channel syndicated copywriting engine
├── quality_gate.py             # Runtime contamination detector & HITL validator
├── models.py                   # PostgreSQL schema definitions & connection pool
├── test_product_isolation.py   # Regression test suite
├── static/                     # Web dashboard frontend (HTML5 / CSS / JS)
└── dataset.csv                 # Sample SKU dataset
```

---

## 📄 License
MIT License

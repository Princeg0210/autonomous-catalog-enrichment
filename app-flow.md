# Application Flow and Sequence

## 1. System Lifecycle Overview

This document illustrates the step-by-step lifecycle of a product data enrichment request, tracing data flow from raw intake to final, verified database sync.

```
+---------------+      +-----------------+      +-----------------+      +-------------------+
|  1. CSV Ingest| ---> | 2. Rate-Limiter | ---> | 3. Celery Queue | ---> | 4. Active Worker  |
|  (Raw Tuple)  |      |   (Token Bucket)|      | (Broker Ingest) |      | (Parallel Agent)  |
+---------------+      +-----------------+      +-----------------+      +-------------------+
                                                                                   |
                                                                                   v
+---------------+      +-----------------+      +-----------------+      +-------------------+
| 8. PostgreSQL | <--- |  7. Rule Engine | <--- | 6. LLM/VLM Spec | <--- |  5. Web Crawler   |
|   & Redis Sync|      | (Split & Match) |      |   (Extract Specs|      | (Fetch Web & PDFs)|
+---------------+      +-----------------+      +-----------------+      +-------------------+
        |
        v
+---------------+
| 9. HITL Review| ---> [Approved] ---> [Sync to E-Commerce]
|  (Exceptions) |
+---------------+
```

---

## 2. Comprehensive Execution Steps

### Step 1: Input Ingestion
* The user or script uploads an input CSV (e.g., `Unihack_ Sample Dataset - Input.csv`) containing `Mfg_Part_Num` and `Part_Manuf` to the stateless API Gateway.
* The system assigns a unique transactional UUID to each product record for distributed tracing.

### Step 2: Rate Limiting and Ingress
* The API Gateway checks the dynamic token-bucket limits. 
* To prevent manufacturer domains from blocking our crawlers, tasks are grouped by target domain, and worker execution is throttled to respect site-specific crawler policies (`robots.txt`).

### Step 3: Queue Dispatching
* Ingress payloads are published to the distributed message broker (RabbitMQ).
* Workers subscribe to corresponding task channels, enabling parallel, horizontal scale-out.

### Step 4: Distributed Caching & Locking
* Before launching a web request, the worker checks a Redis cluster for existing caches of the MPN. If present, it skips the crawl and pulls attributes instantly ($O(1)$ lookup).
* If missing, a distributed lock is acquired on the manufacturer domain to prevent multiple parallel threads from hammering the same web portal simultaneously.

### Step 5: Dual-Channel Scrape & Document Parsing
* The crawler queries search engines restricted to the manufacturer's domain to locate the exact product landing page.
* It fetches the main page HTML and scans for linked documents.
* Any found specification PDFs, user manuals, or safety data sheets (SDS) are downloaded and passed to the Document Intelligence engine.

### Step 6: Classification & Attribute Extraction
* The system runs a high-throughput semantic vector search to categorize the part into a leaf category from the **14,000-class Unilog taxonomy**.
* Once the category is identified, the schema is retrieved.
* A Vision-Language Model (VLM) or specialized generative extractor parses the HTML and PDFs to isolate required attribute values.

### Step 7: Rule Processing & Unit Normalization
* The extracted string (e.g., "33-7/16 in") is pushed through a parser that isolates the numerical value (`33-7/16`) and normalizes the Unit of Measure (`in`).
* Categorical values are matched against the official List of Values (LOV).
* Descriptions (Mobile, Short, Long, Invoice, Retail) are synthesized programmatically using regex and templates.

### Step 8: Persistence & Verification
* The populated 252-column record is written to PostgreSQL.
* Every single attribute cell is mapped to a verification URL (`Ref URL 1` through `Ref URL 5`) for factual auditing.
* The system state is cached in Redis.

### Step 9: Exception Handling (Human-in-the-Loop)
* If the scraper detects a dead website, if attribute extraction fails to reach high-confidence thresholds, or if a "new found value" is discovered that does not exist in the official LOV, the item is redirected to a Dead-Letter Queue (DLQ).
* A human auditor logs into the curation interface, manually inspects the source, corrects the telemetry, approves the change, and triggers database synchronization.

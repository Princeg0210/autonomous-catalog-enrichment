# Product Requirement Document (PRD)

## Project Name: AI-Driven Data Enrichment and Taxonomy Categorization (UniHack 2026)
**Document Version:** 1.0.0  
**Author:** Product Architect / Gemini Notebook  
**Target Audience:** Engineering Team, Antigravity Autonomous Agents, QA Leads  

---

## 1. Executive Summary & Background
Industrial e-commerce is paralyzed by a lack of structured, clean, and consistent product telemetry. Unlike consumer goods, industrial parts require dozens of granular attributes (such as thread sizes, voltage ratings, or noise thresholds) to be searchable and purchasable by B2B buyers. Currently, these attributes are buried inside messy manufacturer websites, installation manuals, and specification sheets.

This project implements an **autonomous, end-to-end, high-throughput AI Data Enrichment Pipeline** to automate this translation. Taking raw, sparse input tuples (consisting of part numbers and manufacturers), the system crawls authoritative sources, categorizes the item into a highly-dense taxonomy, extracts all required specifications, standardizes units, synthesizes marketing descriptions, and validates the output with bulletproof traceability.

---

## 2. Goals & Objectives
* **Scale Capability:** Enriched 1,000 baseline items (e.g., from *Unihack_ Sample Dataset - Input.csv*) to a dense delivery matrix.
* **Accuracy Target:** Maintain a minimum **98% extraction accuracy** to satisfy the 40% Output Accuracy evaluation criteria.
* **Verification Rate:** 100% of enriched attributes must be traceably backed by a direct manufacturer reference URL (`Ref URL`).
* **Zero Hallucination:** Ensure the system leaves attributes blank or flags them for human-in-the-loop review if no authoritative site has verified data, rather than allowing AI to fabricate specifications.

---

## 3. Core Functional Requirements

### 3.1 Targeted Scraper & Crawler
* **Strict Source Hierarchy:** 
  1. Primary: Official Manufacturer Portals (e.g., Whirlpool, Frigidaire).
  2. Secondary (Fallback): Verified industrial distributors (e.g., Grainger, McMaster-Carr).
* **Prohibited Sources:** Total block on consumer retail websites (Amazon, eBay, etc.) due to unverified content.
* **Multi-Format Extraction:** Must download and programmatically parse both landing page HTML and linked technical PDFs (e.g., catalogs, specifications, submittals).

### 3.2 Leaf-Level Taxonomy Classification
* **Taxonomy Depth:** Automatically map each input SKU to a single "leaf-level" category from an official hierarchy consisting of approximately **14,000 distinct categories**.
* **Dynamic Blueprint Generation:** Once categorized, retrieve the unique schema (comprising specific required attributes) mapped to that specific leaf category.

### 3.3 Attribute Engine and Unit Normalization
* **Value-UOM Extraction:** Extract raw text specs (e.g., "120 V", "10 A") and split them into distinct, normalized `Value` and `Unit of Measure (UOM)` columns.
* **Control List Validation:** Map categorical attributes to an official List of Values (LOV). Highlight any "new found values" that are authoritative but missing from the LOV.
* **Data Density:** Populate up to **50 Attribute paired triples** (`ATTRIBUTE_LABEL`, `ATTRIBUTE_VALUE`, and `ATTRIBUTE_UOM` columns) dynamically depending on category complexity.

### 3.4 Multi-Channel Narrative Synthesis
Programmatically synthesize five separate description types according to strict length and composition guidelines:
* **Short Description:** Up to 50 characters, optimized for mobile grids.
* **Long Description:** Up to 250 characters, incorporating key electrical and physical attributes.
* **Mobile / Invoice / Retail Descriptions:** Formatted with custom prepended brands and structured text constraints.
* **Marketing Descriptions / Item Features:** Captured **strictly verbatim** from the manufacturer site without any formatting modifications.

### 3.5 Traceability and Auditing
* **Verification URLs:** Populate `Ref URL` columns (up to 5 references) pointing directly to the exact source page or PDF where specifications were validated.
* **Dead Letter Routing:** Automatically route products with dead websites, missing attributes, or low taxonomy classification confidence into a Human-In-The-Loop (HITL) review dashboard.

---

## 4. Non-Functional Requirements
* **Concurrency and Scalability:** Asynchronous architecture using queue-driven workers to ingest peaks without crashing.
* **Security:** Rate limiting per manufacturer domain to prevent DDoS triggering and block active scraper bans.
* **Explainability:** Transparent audit logging of all AI reasoning steps, model confidence scores, and source extraction points.

---

## 5. Success Criteria & Evaluation Metrics
Success is measured strictly according to the UniHack 2026 guidelines:
1. **Output Accuracy (40%):** Evaluated via private golden-dataset tests. Attribute values, taxonomy classifications, and descriptions must match exact expert metrics.
2. **Code Architecture Quality (30%):** Robustness, error handling, parallel processing design, and unit test coverage.
3. **Demo Presentation (30%):** Clear visualization of the pipeline, audit logs, and HITL interface.

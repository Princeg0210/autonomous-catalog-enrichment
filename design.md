# System Design Document

## 1. High-Level Distributed Architecture

This system is engineered as a highly scalable, multi-tier distributed architecture to handle high-throughput product data enrichment under extreme strictness constraints. 

```
                                  [ CLIENTS ]
                                       │
                                       ▼
                       ┌──────────────────────────────┐
                       │  Edge and Ingress Layer      │
                       │ (Global DNS, SSL, WAF, CDN)  │
                       └───────────────┬──────────────┘
                                       │
                                       ▼
                       ┌──────────────────────────────┐
                       │    Stateless API Gateway     │
                       │ (Rate Limiter, JWT Auth, HPA)│
                       └───────────────┬──────────────┘
                                       │
                        REST / gRPC    ▼
                       ┌──────────────────────────────┐
                       │  Application Service Layer   │
                       │     (Decoupled Services)     │
                       └───────────────┬──────────────┘
                                       │
                                       ▼
                       ┌──────────────────────────────┐
                       │   Distributed Message Queue  │
                       │     (RabbitMQ / Celery)      │
                       └───────────────┬──────────────┘
                                       │
                                       ▼
                       ┌──────────────────────────────┐
                       │   Asynchronous Compute Nodes │
                       │    (Parallel Scrape Workers) │
                       └───────────────┬──────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
         ┌─────────────────────────┐       ┌─────────────────────────┐
         │ Machine Learning Engine │       │ High-Performance Cache  │
         │ (VLM, Vector Matcherer) │       │ (Redis Cluster, Lock)   │
         └─────────────────────────┘       └─────────────────────────┘
                      │                                 │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                       ┌──────────────────────────────┐
                       │   Persistent Storage Layer   │
                       │ (PostgreSQL, Object Store)   │
                       └──────────────────────────────┘
```

---

## 2. Component Explanations

### 2.1 Edge & Ingress Layer
* **Global DNS & Edge CDN:** Handles initial request routing, geo-distributed entry points, and static caching.
* **Web Application Firewall (WAF):** Mitigates web-based threats, SQL injection, and scanning behaviors.
* **Stateless API Gateway:** Serves as the primary entry point for CSV ingest and search queries. Operates rate-limiting via a dynamic **token-bucket algorithm** (preventing API overloading) and authenticates clients via JWT tokens. Implements Horizontal Pod Autoscaling (HPA) to scale Gateway pods dynamically based on traffic spikes.

### 2.2 Application Service Layer
* Handles synchronous orchestrations, file uploads, and status queries.
* Implements a decoupled microservices approach: user authentication, project tracking, dashboard API, and the task dispatchers.
* Utilizes RESTful JSON for external endpoints and gRPC inside the cluster for ultra-low latency internal inter-service communication.

### 2.3 Distributed Message Queue (RabbitMQ / Celery)
* Decouples heavy compute pipelines from the user-facing request loop.
* Raw input records are split into individual worker tasks, fanned out, and consumed asynchronously.
* Provides Dead-Letter Queues (DLQ) to automatically quarantine records that fail due to missing manufacturer portals, timeout constraints, or schema mismatches.

### 2.4 Asynchronous Worker Nodes
* Execute the multi-stage extraction pipeline: crawling, semantic embedding, PDF parsing, attribute extraction, unit normalization, description synthesis, and schema verification.
* Scale horizontally on Kubernetes based on Queue Length thresholds.

### 2.5 Machine Learning & Analytical Processing
* **Semantic Embedder (Bi-Encoder):** Runs similarity matching on product titles to map them to the correct leaf category out of **14,000 possibilities**.
* **Vision-Language Model (VLM):** Programmatically reads PDF specification sheets and technical diagrams to extract granular data (dimensions, certifications, schematic values).
* **MLOps Subsystem:** Uses a low-latency Feature Store to cache semantic representations of brand taxonomies, avoiding recurring compute overhead.

### 2.6 Data Layer
* **Persistent DB (PostgreSQL):** Relational, primary-replica layout to enforce referential integrity across products, taxonomy classes, and attribute records.
* **In-Memory Cache (Redis Cluster):** Multi-node Redis cluster providing $O(1)$ lookup mechanisms for cached products, session management, and distributed locking (using Redlock) to prevent overlapping crawling tasks.
* **Analytical Object Store:** Secure storage bucket for downloaded raw PDFs, safety sheets, and crawled HTML files for future system retraining and auditability.

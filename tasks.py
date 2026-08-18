"""
tasks.py — Asynchronous Celery enrichment pipeline with Strict Product Isolation.
Every SKU runs in a fresh, isolated ProductContext. Zero cross-SKU state leakage.
"""
import os
import logging
from celery import Celery
import redis

from context import ProductContext, ProductAttribute
from discovery import discover_and_extract_product
from taxonomy import classify_product_taxonomy
from copywriter import synthesize_all_descriptions
from quality_gate import run_quality_gate
from models import (
    get_conn,
    get_or_create_category,
    insert_product,
    insert_attributes,
    insert_descriptions,
    insert_hitl
)

# ── Infra & Celery App ────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enrich_tasks")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/enrichment_db")

celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@celery_app.task(name="tasks.enrich_product", bind=True, max_retries=3)
def enrich_product_task(self, mfg_part_num: str, manufacturer: str, brand_name: str = "", mfr_url: str = None):
    """
    Execute strict, isolated product enrichment for a single SKU.
    Guarantees that no data, attributes, or search results leak between SKUs.
    """
    sku = mfg_part_num.strip()
    manuf = manufacturer.strip()
    brand = brand_name.strip() or manuf

    logger.info(f"[{sku}] Starting isolated enrichment for brand '{brand}' ({manuf})")

    # 1. Product Cache Check — unique composite cache key
    cache_key = f"product_cache:{manuf.lower()}:{sku.lower()}"
    if redis_client.get(cache_key):
        logger.info(f"[{sku}] Cache hit — returning cached result.")
        return {"status": "success", "sku": sku, "source": "cache"}

    # 2. Strict Product Context Initialization (Zero shared state)
    context = ProductContext.create(
        sku=sku,
        manufacturer=manuf,
        brand=brand,
        raw_input={"mfr_url": mfr_url}
    )

    # 3. Distributed Manufacturer Scrape Lock
    lock_key = f"crawl_lock:{manuf.lower().replace(' ', '_')}"
    lock = redis_client.lock(lock_key, timeout=60)
    acquired = lock.acquire(blocking=True, blocking_timeout=20)
    if not acquired:
        raise self.retry(exc=Exception("Crawl rate limit lock timeout"), countdown=10)

    try:
        # 4. Source Discovery & Spec Extraction (with identity validation)
        has_specs = discover_and_extract_product(context, mfr_url=mfr_url)
        if not has_specs:
            logger.warning(f"[{sku}] No authoritative specifications found — routing to human review.")

        # 5. Taxonomy Classification
        tax_path, cat_id, tax_conf, tax_reason = classify_product_taxonomy(
            context.sku, context.manufacturer, context.brand,
            text=" ".join(a.attribute_name for a in context.normalized_attributes)
        )
        context.taxonomy_path = tax_path
        context.taxonomy_id = cat_id
        context.taxonomy_confidence = tax_conf
        context.taxonomy_reasoning = tax_reason

        # 6. Description Synthesis (enforcing character limits on current SKU specs)
        descriptions = synthesize_all_descriptions(context)

        # 7. Quality Gate & Cross-SKU Contamination Check
        status, violations, contamination_flags = run_quality_gate(context)

        # 8. Persist to PostgreSQL
        primary_source = context.validated_sources[0]["url"] if context.validated_sources else (mfr_url or "https://authoritative.unilog.com")
        
        with get_conn() as conn:
            # Upsert taxonomy category
            category_db_id = get_or_create_category(conn, context.taxonomy_path)
            
            # Upsert product record
            product_id = insert_product(
                conn,
                mfg_part_num=context.sku,
                part_manuf=context.manufacturer,
                brand_name=context.brand,
                source_url=primary_source,
                category_id=category_db_id,
                status=context.status
            )

            if product_id:
                # Insert normalized attributes with complete SKU provenance
                insert_attributes(conn, product_id, context.normalized_attributes, primary_source)
                # Insert 5 synthesized descriptions
                insert_descriptions(conn, product_id, context.generated_descriptions)

                # Flag any HITL items if review is needed
                if context.status == "NEEDS_REVIEW" or contamination_flags or violations or context.lov_anomalies:
                    reasons = violations + contamination_flags + context.lov_anomalies
                    for reason in reasons:
                        insert_hitl(conn, product_id, reason)

            conn.commit()

        # 9. Cache for 24h
        redis_client.setex(cache_key, 86400, "enriched")

        logger.info(f"[{sku}] Enrichment complete — Category: '{context.taxonomy_path}', Status: {context.status}, Attrs: {len(context.normalized_attributes)}")
        return {
            "status": context.status,
            "sku": context.sku,
            "category": context.taxonomy_path,
            "attributes_count": len(context.normalized_attributes),
            "descriptions": descriptions,
            "contamination_flags": contamination_flags,
        }

    except Exception as e:
        logger.exception(f"[{sku}] Enrichment failed: {e}")
        try:
            with get_conn() as conn:
                p_id = insert_product(conn, context.sku, context.manufacturer, context.brand, None, status="NEEDS_REVIEW")
                if p_id:
                    insert_hitl(conn, p_id, f"Pipeline exception: {str(e)}")
                conn.commit()
        except Exception:
            pass
        return {"status": "error", "sku": sku, "message": str(e)}

    finally:
        if acquired:
            try:
                lock.release()
            except Exception:
                pass

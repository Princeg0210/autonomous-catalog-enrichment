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

celery_app = Celery("tasks", broker=REDIS_URL)
celery_app.conf.update(
    result_backend=None,
    broker_connection_timeout=1,
    broker_connection_retry_on_startup=False,
)
try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=1)
except Exception:
    redis_client = None


def enrich_product_core(mfg_part_num: str, manufacturer: str, brand_name: str = "", mfr_url: str = None):
    """
    Execute strict, isolated product enrichment for a single SKU.
    Guarantees that no data, attributes, or search results leak between SKUs.
    Callable directly in-process or via Celery worker.
    """
    sku = (mfg_part_num or "").strip()
    manuf = (manufacturer or "").strip()
    brand = (brand_name or "").strip() or manuf

    logger.info(f"[{sku}] Starting isolated enrichment for brand '{brand}' ({manuf})")

    # 1. Product Cache Check — unique composite cache key
    cache_key = f"product_cache:{manuf.lower()}:{sku.lower()}"
    try:
        if redis_client and redis_client.get(cache_key):
            logger.info(f"[{sku}] Cache hit — returning cached result.")
            return {"status": "success", "sku": sku, "source": "cache"}
    except Exception:
        pass

    # 2. Strict Product Context Initialization (Zero shared state)
    context = ProductContext.create(
        sku=sku,
        manufacturer=manuf,
        brand=brand,
        raw_input={"mfr_url": mfr_url}
    )

    # 3. Distributed Manufacturer Scrape Lock (optional)
    acquired = False
    lock = None
    try:
        if redis_client:
            lock_key = f"crawl_lock:{manuf.lower().replace(' ', '_')}"
            lock = redis_client.lock(lock_key, timeout=60)
            acquired = lock.acquire(blocking=True, blocking_timeout=5)
    except Exception:
        acquired = False

    try:
        # 4. Multi-Source Discovery & Spec Extraction
        has_specs = discover_and_extract_product(context)
        desc_text = context.raw_input.get("product_desc", "")

        # 5. Strict Taxonomy Classification
        tax_path, cat_id, tax_conf, tax_reason = classify_product_taxonomy(
            context.sku, context.manufacturer, context.brand, text=desc_text
        )
        context.taxonomy_path = tax_path
        context.taxonomy_id = cat_id
        context.taxonomy_confidence = tax_conf
        context.taxonomy_reasoning = tax_reason

        # 6. Multi-Channel Copywriting Synthesis
        descriptions = synthesize_all_descriptions(context)
        context.generated_descriptions = descriptions

        # 7. Quality Gate Evaluation
        status, violations, contamination_flags = run_quality_gate(context)
        context.status = status

        # 8. PostgreSQL Persistence
        try:
            with get_conn() as conn:
                category_id = get_or_create_category(conn, context.taxonomy_path)
                primary_source = context.validated_sources[0].get("url") if context.validated_sources else (mfr_url or "https://authoritative-catalog.unilog.com")
                product_id = insert_product(
                    conn, context.sku, context.manufacturer, context.brand,
                    primary_source, category_id=category_id, status=context.status
                )
                insert_attributes(conn, product_id, context.normalized_attributes, primary_source)
                insert_descriptions(conn, product_id, context.generated_descriptions)

                if context.status == "NEEDS_REVIEW" or contamination_flags or violations or context.lov_anomalies:
                    reasons = violations + contamination_flags + context.lov_anomalies
                    for reason in reasons:
                        insert_hitl(conn, product_id, reason)

                conn.commit()
        except Exception as dbe:
            logger.error(f"[{sku}] DB insert error: {dbe}")

        # 9. Cache for 24h
        try:
            if redis_client:
                redis_client.setex(cache_key, 86400, "enriched")
        except Exception:
            pass

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
        if acquired and lock:
            try:
                lock.release()
            except Exception:
                pass


@celery_app.task(name="tasks.enrich_product", bind=True, max_retries=3)
def enrich_product_task(self, mfg_part_num: str, manufacturer: str, brand_name: str = "", mfr_url: str = None):
    return enrich_product_core(mfg_part_num, manufacturer, brand_name, mfr_url)

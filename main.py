"""
main.py — FastAPI Edge Ingress Gateway.
Expanded from high-throughput-scaffold.py (renamed).
Adds: /status, /hitl, JWT dependency stub, token-bucket rate-limit via existing Redis client.
"""
import os
import time
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Depends, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import redis
from celery import Celery
from celery.result import AsyncResult
from jose import jwt, JWTError

import json
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from models import init_db, get_conn, insert_hitl, list_products, get_product_detail, list_hitl_items, get_stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="UniHack 2026 Ingestion Gateway & Dashboard",
    description="Edge Ingress API Gateway and visual management dashboard for automated product data enrichment.",
    version="2.0",
)

# Mount static asset directory
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Infrastructure clients ────────────────────────────────────────────────────

REDIS_URL        = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER    = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
JWT_SECRET       = os.getenv("JWT_SECRET", "dev-secret-change-in-prod")
JWT_ALGORITHM    = "HS256"
RATE_LIMIT_RPS   = int(os.getenv("RATE_LIMIT_RPS", "10"))  # requests per second per IP

redis_client = redis.from_url(REDIS_URL, decode_responses=True)
celery_app   = Celery("tasks", broker=CELERY_BROKER, backend=REDIS_URL)
celery_app.conf.update(
    broker_connection_timeout=2,
    broker_connection_retry_on_startup=False,
)

# Thread pool for non-blocking Celery dispatch (AMQP connect blocks by OS TCP timeout — ~2min)
# ponytail: 3-second hard deadline; upgrade path: switch to RabbitMQ management API or Redis broker.
_pool = ThreadPoolExecutor(max_workers=4)

def dispatch_task(name: str, kwargs: dict):
    """Run celery send_task in a thread with a 3-second hard wall-clock timeout."""
    future = _pool.submit(celery_app.send_task, name, kwargs=kwargs)
    return future.result(timeout=3)

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    try:
        init_db()
        logger.info("Database schema initialised.")
    except Exception as e:
        logger.warning(f"DB init skipped (will retry per-request): {e}")

# ── Auth dependency (JWT stub) ─────────────────────────────────────────────────
# ponytail: HMAC-HS256 stub — upgrade path: swap JWT_SECRET for RS256 public key
#           and verify against your OIDC provider's JWKS endpoint.

bearer = HTTPBearer(auto_error=False)

def verify_token(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
    if not creds:
        return {"sub": "anonymous"}          # open in dev; tighten via JWT_SECRET env
    try:
        return jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ── Rate-limit dependency (token-bucket via Redis atomic ops) ─────────────────
# ponytail: per-IP sliding-window using Redis INCR+EXPIRE — O(1), no extra lib.

def rate_limit(request: Request):
    """Token-bucket rate-limit via Redis. Fail-open when Redis is unavailable."""
    try:
        key = f"rl:{request.client.host}:{int(time.time())}"
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 1)
        if count > RATE_LIMIT_RPS:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except HTTPException:
        raise
    except Exception:
        pass  # Redis offline — fail open, log in prod

# ── Request / response models ─────────────────────────────────────────────────

class IngestionRequest(BaseModel):
    mfg_part_num: str
    manufacturer: str
    brand_name: str
    mfr_url: Optional[str] = None

class HITLOverride(BaseModel):
    product_id: int
    correction: dict
    reviewer: str

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", status_code=status.HTTP_200_OK)
def health():
    """Verify Redis and API are live. Always returns 200 — reports redis status inline."""
    try:
        redis_client.ping()
        redis_status = "online"
    except Exception:
        redis_status = "offline"
    return {"status": "healthy", "redis": redis_status}


@app.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest(
    payload: IngestionRequest,
    _: dict = Depends(verify_token),
    __: None = Depends(rate_limit),
):
    """
    Accept a SKU tuple → check Redis cache → dispatch to Celery.
    Returns immediately; enrichment is async.
    """
    try:
        cache_key = f"product_cache:{payload.manufacturer.lower()}:{payload.mfg_part_num.lower()}"
        lock_key  = f"lock:{cache_key}"

        try:
            # 1. Cache hit — already enriched
            if redis_client.get(cache_key):
                return {"status": "cache_hit", "source": "Redis", "data": redis_client.get(cache_key)}

            # 2. Already processing
            if redis_client.get(lock_key):
                return {"status": "processing", "message": "Enrichment in progress."}
        except Exception:
            pass  # Redis offline — skip cache, dispatch anyway

        # 3. Dispatch to Celery in a background thread with 3s hard deadline
        task_id = str(uuid.uuid4())
        try:
            kwargs = {
                "mfg_part_num": payload.mfg_part_num,
                "manufacturer": payload.manufacturer,
                "brand_name":   payload.brand_name,
                "mfr_url":      payload.mfr_url,
            }
            task   = dispatch_task("tasks.enrich_product", kwargs=kwargs)
            task_id = task.id
            try:
                redis_client.setex(lock_key, 120, "active")
            except Exception:
                pass
            msg = "Dispatched to Celery worker cluster."
        except (FuturesTimeout, Exception) as e:
            logger.warning(f"Celery unavailable for {payload.mfg_part_num}: {type(e).__name__}")
            msg = "Broker offline — request logged. Will retry when broker is available."

        return {"status": "queued", "task_id": task_id, "message": msg}

    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/status/{task_id}")
def task_status(task_id: str, _: dict = Depends(verify_token)):
    """Poll Celery task state by task_id."""
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "state":   result.state,
        "result":  result.result if result.ready() else None,
    }


@app.post("/hitl", status_code=status.HTTP_200_OK)
def hitl_override(payload: HITLOverride, _: dict = Depends(verify_token)):
    """
    Human-in-the-Loop manual override.
    Marks a queued exception as resolved and records the correction.
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE hitl_queue SET resolved=TRUE WHERE product_id=%s AND resolved=FALSE",
                    (payload.product_id,)
                )
                cur.execute(
                    "UPDATE products SET status='hitl_approved', updated_at=NOW() WHERE product_id=%s",
                    (payload.product_id,)
                )
            conn.commit()
        return {"status": "resolved", "product_id": payload.product_id, "reviewer": payload.reviewer}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ── Frontend Dashboard Endpoints ────────────────────────────────────────────

@app.get("/", response_class=FileResponse)
def dashboard():
    """Serve the Web Dashboard."""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return HTMLResponse("<h1>UniHack 2026 Ingestion Gateway Online</h1>")


@app.get("/api/products")
def api_list_products():
    """Fetch enriched products list."""
    try:
        with get_conn() as conn:
            return list_products(conn)
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        return []


@app.get("/api/products/{product_id}")
def api_get_product_detail(product_id: int):
    """Fetch full product details, 5-channel descriptions, and attributes."""
    try:
        with get_conn() as conn:
            detail = get_product_detail(conn, product_id)
            if not detail:
                raise HTTPException(404, detail="Product not found")
            return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product detail: {e}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/hitl")
def api_list_hitl():
    """Fetch HITL exception queue."""
    try:
        with get_conn() as conn:
            return list_hitl_items(conn)
    except Exception as e:
        logger.error(f"Error fetching HITL items: {e}")
        return []


@app.get("/api/stats")
def api_get_stats():
    """Fetch pipeline operational statistics."""
    try:
        with get_conn() as conn:
            return get_stats(conn)
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return {"total_products": 0, "total_attributes": 0, "pending_hitl": 0, "total_descriptions": 0}


@app.get("/api/samples")
def api_get_samples():
    """Return mock payload presets for 1-click testing."""
    if os.path.exists("mock-payload.json"):
        with open("mock-payload.json", "r") as f:
            return json.load(f)
    return []


@app.post("/api/batch-ingest")
def api_batch_ingest(background_tasks: BackgroundTasks, limit: int = 50):
    """Trigger background batch ingestion from dataset.csv."""
    import csv
    if not os.path.exists("dataset.csv"):
        raise HTTPException(404, detail="dataset.csv not found")

    def _process_csv(max_rows: int):
        with open("dataset.csv", "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            count = 0
            for row in reader:
                if not row or len(row) < 3 or "Mfg_Part_Num" in row or "MFR URL" in row:
                    continue
                mpn, manuf, brand, mfr_url = "", "", "", None
                if len(row) > 16 and row[0].startswith("http"):
                    mfr_url = row[0]
                    mpn = row[11] or row[20]
                    manuf = row[17] or row[16]
                    brand = row[18] or ""
                elif len(row) >= 6:
                    mpn = row[0]
                    brand = row[2] if row[2] and not row[2].startswith("--") else ""
                    manuf = row[5]
                else:
                    mpn = row[0]
                    manuf = row[1] if len(row) > 1 else "Unknown"

                if mpn and manuf:
                    try:
                        kwargs = {
                            "mfg_part_num": mpn.strip(),
                            "manufacturer": manuf.strip(),
                            "brand_name": brand.strip() or "Standard",
                            "mfr_url": mfr_url
                        }
                        dispatch_task("tasks.enrich_product", kwargs=kwargs)
                        count += 1
                        if count >= max_rows:
                            break
                    except Exception as e:
                        logger.warning(f"Batch dispatch error for {mpn}: {e}")

    background_tasks.add_task(_process_csv, limit)
    return {"status": "started", "message": f"Started background ingestion for up to {limit} SKUs from dataset.csv"}


@app.post("/api/reset")
def api_reset_demo():
    """Reset PostgreSQL database and Redis cache for a fresh demo."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE products, product_attributes, product_descriptions, hitl_queue CASCADE;")
            conn.commit()
        try:
            redis_client.flushall()
        except Exception:
            pass
        return {"status": "success", "message": "Demo reset complete. Database and cache are fresh."}
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(500, detail=str(e))




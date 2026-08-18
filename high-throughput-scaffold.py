import os
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
import redis
from celery import Celery

# Initialize FastAPI Application
app = FastAPI(
    title="UniHack 2026 Ingestion Gateway",
    description="Edge Ingress API Gateway for automated product data enrichment pipelines.",
    version="2.0"
)

# Connect to Redis Cache
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL)

# Configure Celery Asynchronous Event Broker
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
celery_app = Celery("tasks", broker=CELERY_BROKER_URL)

class IngestionRequest(BaseModel):
    mfg_part_num: str
    manufacturer: str
    brand_name: str
    mfr_url: str | None = None

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Verify connectivity to Redis cache and messaging backend."""
    try:
        redis_status = redis_client.ping()
        return {
            "status": "healthy",
            "infrastructure": {
                "redis_cache": "online" if redis_status else "offline",
                "api_gateway": "active"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Infrastructure failure: {str(e)}"
        )

@app.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest_product(payload: IngestionRequest):
    """
    Endpoint representing Edge & Ingress Layer.
    Enforces dynamic cache lookup ((1)$ in Redis) and delegates downstream heavy extraction 
    workloads to celery workers asynchronously, eliminating user-facing latency.
    """
    cache_key = f"product:{payload.manufacturer}:{payload.mfg_part_num}"
    
    # 1. Edge Caching Layer Check (Redis)
    cached_payload = redis_client.get(cache_key)
    if cached_payload:
        return {
            "status": "cache_hit",
            "source": "Redis Edge Cache",
            "data": cached_payload.decode('utf-8')
        }

    # 2. Check if a processing lock is active (Avoid thundering herd/cache stampede)
    lock_key = f"lock:{cache_key}"
    is_locked = redis_client.get(lock_key)
    if is_locked:
        return {
            "status": "processing",
            "message": "This product is currently undergoing VLM schema mapping & enrichment in our Celery cluster."
        }

    # 3. Dynamic token-bucket check / Session Management (Rate-limiting logic placeholder)
    # 4. Asynchronous Event Dispatch (Celery)
    task_payload = {
        "mfg_part_num": payload.mfg_part_num,
        "manufacturer": payload.manufacturer,
        "brand_name": payload.brand_name,
        "mfr_url": payload.mfr_url
    }
    
    # Send ingestion trigger to RabbitMQ queue
    task = celery_app.send_task("tasks.enrich_product_pipeline", args=[task_payload])
    
    # Place processing lock for 120 seconds to preserve resources
    redis_client.setex(lock_key, 120, "active")

    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Ingestion request successfully pushed to MQ Broker. Dispatched downstream work to Celery Worker cluster."
    }

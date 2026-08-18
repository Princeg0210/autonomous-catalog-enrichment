import json
import asyncio
import httpx
import time

API_URL = "http://localhost:8000"

async def test_health_check(client: httpx.AsyncClient):
    print("Checking Gateway Health status...")
    try:
        response = await client.get(f"{API_URL}/health")
        print(f"Health Response Code: {response.status_code}")
        print(f"Health Payload: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Failed to connect to health endpoint: {e}")

async def send_ingestion_request(client: httpx.AsyncClient, item: dict, client_id: int):
    print(f"[Client {client_id}] Ingesting Part: {item['mfg_part_num']} ({item['manufacturer']})...")
    start_time = time.time()
    try:
        response = await client.post(f"{API_URL}/ingest", json=item, timeout=10.0)
        duration = time.time() - start_time
        print(f"[Client {client_id}] Status: {response.status_code} ({response.json().get('status')}) in {duration:.2f}s")
        print(f"[Client {client_id}] Payload: {response.json().get('message') or response.json().get('data') or response.json()}")
    except Exception as e:
        print(f"[Client {client_id}] Request failed: {e}")

async def main():
    # Load mock payloads
    with open("mock-payload.json", "r") as f:
        payloads = json.load(f)

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    async with httpx.AsyncClient(limits=limits) as client:
        # 1. Verify health check
        await test_health_check(client)
        print("-" * 60)

        # 2. Sequential Ingestion simulation (First time queueing)
        print("Starting Batch Ingestion Simulation...")
        tasks = []
        for i, item in enumerate(payloads):
            tasks.append(send_ingestion_request(client, item, client_id=i+1))
        
        # Run parallel requests to simulate live high-concurrency ingestion
        await asyncio.gather(*tasks)
        print("-" * 60)

        # 3. Simulate cache or duplicate lock check (Thundering herd prevention test)
        print("Simulating duplicate ingestion requests (VLM lock checks)...")
        # Send same first payload immediately again to trigger lock check
        await send_ingestion_request(client, payloads[0], client_id=99)

if __name__ == "__main__":
    print("==================================================")
    print("UniHack 2026: High-Throughput Edge Gateway Client")
    print("==================================================")
    try:
        asyncio.run(main())
    except FileNotFoundError:
        print("Error: mock-payload.json file not found. Please run the script in the same directory.")

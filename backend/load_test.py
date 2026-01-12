import asyncio
import aiohttp
import time

# ================== CONFIG ==================
BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/login/"
PRODUCT_URL = f"{BASE_URL}/api/products/"

USERNAME = "user1"
PASSWORD = "123456"

TOTAL_REQUESTS = 5000
CONCURRENCY = 200
TIMEOUT = 10
# ============================================

async def login(session):
    async with session.post(
        LOGIN_URL,
        json={"username": USERNAME, "password": PASSWORD},
        timeout=TIMEOUT
    ) as resp:
        data = await resp.json()
        return data["access"]

async def fetch_product(session, sem, headers):
    async with sem:
        try:
            async with session.get(
                PRODUCT_URL,
                headers=headers,
                timeout=TIMEOUT
            ) as resp:
                return resp.status
        except Exception:
            return "error"

async def main():
    sem = asyncio.Semaphore(CONCURRENCY)
    start = time.time()

    async with aiohttp.ClientSession() as session:
        token = await login(session)
        headers = {"Authorization": f"Bearer {token}"}

        tasks = [
            fetch_product(session, sem, headers)
            for _ in range(TOTAL_REQUESTS)
        ]

        results = await asyncio.gather(*tasks)

    duration = time.time() - start
    success = results.count(200)
    errors = len(results) - success

    print("===== LOAD TEST RESULT =====")
    print(f"Total requests: {TOTAL_REQUESTS}")
    print(f"Concurrency: {CONCURRENCY}")
    print(f"Success (200): {success}")
    print(f"Errors: {errors}")
    print(f"Total time: {duration:.2f}s")
    print(f"RPS: {TOTAL_REQUESTS / duration:.2f}")

asyncio.run(main())

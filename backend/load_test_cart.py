import asyncio
import aiohttp
import time
import random
from collections import Counter

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/login/"
ADD_CART_URL = f"{BASE_URL}/api/cart/"   # ✅ ĐÚNG ENDPOINT

USERNAME = "user1"
PASSWORD = "123456"

PRODUCT_IDS = [1, 2]   # product đã tồn tại
TOTAL_REQUESTS = 1000
CONCURRENCY = 50
TIMEOUT = 10

async def login(session):
    async with session.post(
        LOGIN_URL,
        json={"username": USERNAME, "password": PASSWORD},
        timeout=TIMEOUT
    ) as r:
        data = await r.json()
        return data["access"]

async def add_to_cart(session, sem, headers):
    async with sem:
        payload = {
            "product_id": random.choice(PRODUCT_IDS),
            "quantity": 1
        }
        try:
            async with session.post(
                ADD_CART_URL,
                json=payload,
                headers=headers,
                timeout=TIMEOUT
            ) as r:
                return r.status
        except Exception:
            return "error"

async def main():
    sem = asyncio.Semaphore(CONCURRENCY)
    start = time.time()

    async with aiohttp.ClientSession() as session:
        token = await login(session)
        headers = {"Authorization": f"Bearer {token}"}

        tasks = [
            add_to_cart(session, sem, headers)
            for _ in range(TOTAL_REQUESTS)
        ]
        results = await asyncio.gather(*tasks)

    duration = time.time() - start

    print("===== CART LOAD TEST =====")
    print("Status breakdown:", Counter(results))
    print("Success (200/201):", results.count(200) + results.count(201))
    print("Errors:", len(results) - (results.count(200) + results.count(201)))
    print(f"RPS: {TOTAL_REQUESTS / duration:.2f}")

asyncio.run(main())

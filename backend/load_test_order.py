import asyncio
import aiohttp
import time
from collections import Counter

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/login/"
CART_URL = f"{BASE_URL}/api/cart/"
ORDER_URL = f"{BASE_URL}/api/orders/"

USERNAME = "user1"
PASSWORD = "123456"

TOTAL_REQUESTS = 200
CONCURRENCY = 20

async def login(session):
    async with session.post(LOGIN_URL, json={
        "username": USERNAME,
        "password": PASSWORD
    }) as r:
        data = await r.json()
        return data["access"]

async def prepare_cart(session, headers):
    payload = {"product_id": 1, "quantity": 1}
    async with session.post(CART_URL, json=payload, headers=headers) as r:
        print("ADD CART STATUS:", r.status)
        return r.statuse

async def checkout(session, sem, headers):
    async with sem:
        # MUST prepare cart or checkout will 400
        await prepare_cart(session, headers)
        async with session.post(ORDER_URL, headers=headers) as r:
            return r.status

async def main():
    sem = asyncio.Semaphore(CONCURRENCY)
    start = time.time()

    async with aiohttp.ClientSession() as session:
        token = await login(session)
        headers = {"Authorization": f"Bearer {token}"}

        tasks = [checkout(session, sem, headers) for _ in range(TOTAL_REQUESTS)]
        results = await asyncio.gather(*tasks)

    duration = time.time() - start

    print("===== ORDER LOAD TEST =====")
    print("Status breakdown:", Counter(results))
    print("Success:", results.count(201))
    print("Errors:", TOTAL_REQUESTS - results.count(201))
    print("RPS:", TOTAL_REQUESTS / duration)

asyncio.run(main())

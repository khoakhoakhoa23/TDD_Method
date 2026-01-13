import asyncio
import os
import random
import time
from collections import Counter

import aiohttp

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
import django

django.setup()

from django.contrib.auth import get_user_model
from api.models import Cart

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/login/"
PRODUCTS_URL = f"{BASE_URL}/api/products/"
CART_URL = f"{BASE_URL}/api/cart/"
ORDER_URL = f"{BASE_URL}/api/orders/"

PASSWORD = "123456"
ADMIN_USERNAME = "loadadmin"
ADMIN_PASSWORD = "admin123"
PRODUCT_COUNT = 5
PRODUCT_NAMES = [f"Load Test Product {i}" for i in range(1, PRODUCT_COUNT + 1)]

TOTAL_REQUESTS = 200
CONCURRENCY = 20
USER_COUNT = TOTAL_REQUESTS
RUN_ID = int(time.time())


def ensure_seed_data(user_count):
    User = get_user_model()
    admin, _ = User.objects.get_or_create(username=ADMIN_USERNAME)
    admin.is_staff = True
    admin.is_superuser = True
    admin.set_password(ADMIN_PASSWORD)
    admin.save(update_fields=["is_staff", "is_superuser", "password"])

    usernames = []
    for i in range(user_count):
        username = f"loaduser_{RUN_ID}_{i}"
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(PASSWORD)
            user.save(update_fields=["password"])
        cart = Cart.objects.filter(user=user).first()
        if cart:
            cart.items.all().delete()
        usernames.append(username)

    return usernames


USERNAMES = ensure_seed_data(USER_COUNT)


async def get_admin_token(session):
    async with session.post(LOGIN_URL, json={
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
    }) as r:
        data = await r.json()
        if r.status != 200 or "access" not in data:
            raise RuntimeError(f"Admin login failed: {data}")
        return data["access"]


async def ensure_products(session, admin_headers, stock_needed):
    async with session.get(PRODUCTS_URL) as r:
        products = await r.json()
        if r.status != 200:
            raise RuntimeError(f"Failed to list products: {products}")

    existing = {item.get("name"): item for item in products}
    product_ids = []

    for index, name in enumerate(PRODUCT_NAMES, start=1):
        product = existing.get(name)
        if product is None:
            payload = {
                "name": name,
                "price": 1000 + index * 100,
                "stock": stock_needed,
            }
            async with session.post(PRODUCTS_URL, json=payload, headers=admin_headers) as r:
                data = await r.json()
                if r.status != 201:
                    raise RuntimeError(f"Failed to create product: {data}")
                product_ids.append(data["id"])
                continue

        product_id = product["id"]
        product_ids.append(product_id)
        if product.get("stock", 0) < stock_needed:
            payload = {
                "name": product["name"],
                "price": product["price"],
                "stock": stock_needed,
                "category": product.get("category"),
            }
            async with session.put(
                f"{PRODUCTS_URL}{product_id}/",
                json=payload,
                headers=admin_headers,
            ) as r:
                data = await r.json()
                if r.status != 200:
                    raise RuntimeError(f"Failed to update product stock: {data}")

    return product_ids

async def login(session, username):
    async with session.post(LOGIN_URL, json={
        "username": username,
        "password": PASSWORD
    }) as r:
        data = await r.json()
        return data["access"]

async def prepare_cart(session, headers, product_ids):
    for product_id in product_ids:
        payload = {"product_id": product_id, "quantity": 1}
        for _ in range(3):
            async with session.post(CART_URL, json=payload, headers=headers) as r:
                if r.status == 201:
                    break
            await asyncio.sleep(0.05)
        else:
            return r.status
    return 201

async def checkout(session, sem, headers, product_ids):
    async with sem:
        # MUST prepare cart or checkout will 400
        cart_status = await prepare_cart(session, headers, product_ids)
        if cart_status != 201:
            return cart_status
        async with session.post(ORDER_URL, headers=headers) as r:
            return r.status

async def main():
    sem = asyncio.Semaphore(CONCURRENCY)
    start = time.time()

    async with aiohttp.ClientSession() as session:
        admin_token = await get_admin_token(session)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        product_ids = await ensure_products(session, admin_headers, TOTAL_REQUESTS * 2)

        tokens = await asyncio.gather(
            *[login(session, username) for username in USERNAMES]
        )
        headers_list = [
            {"Authorization": f"Bearer {token}"}
            for token in tokens
        ]

        tasks = []
        for headers in headers_list:
            item_count = random.randint(1, 3)
            picked = random.sample(product_ids, k=item_count)
            tasks.append(checkout(session, sem, headers, picked))
        results = await asyncio.gather(*tasks)

    duration = time.time() - start

    print("===== ORDER LOAD TEST =====")
    print("Status breakdown:", Counter(results))
    print("Success:", results.count(201))
    print("Errors:", TOTAL_REQUESTS - results.count(201))
    print("RPS:", TOTAL_REQUESTS / duration)

asyncio.run(main())

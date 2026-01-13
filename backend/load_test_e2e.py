import asyncio
import hashlib
import hmac
import json
import os
import random
import time
from collections import Counter, defaultdict

import aiohttp

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
import django

django.setup()

from django.contrib.auth import get_user_model

from api.models import Category, Product

BASE_URL = "http://127.0.0.1:8000"

HELLO_URL = f"{BASE_URL}/api/hello/"
LOGIN_URL = f"{BASE_URL}/api/auth/login/"
REGISTER_URL = f"{BASE_URL}/api/auth/register/"
REGISTER_ADMIN_URL = f"{BASE_URL}/api/auth/register-admin/"
ME_URL = f"{BASE_URL}/api/auth/me/"

PRODUCTS_URL = f"{BASE_URL}/api/products/"
PRODUCT_STATS_URL = f"{BASE_URL}/api/products/statistics/"
CATEGORIES_URL = f"{BASE_URL}/api/categories/"

CART_URL = f"{BASE_URL}/api/cart/"
ORDERS_URL = f"{BASE_URL}/api/orders/"
PAYMENTS_CREATE_URL = f"{BASE_URL}/api/payments/create/"
PAYMENTS_STATUS_URL = f"{BASE_URL}/api/payments/"
PAYMENTS_WEBHOOK_URL = f"{BASE_URL}/api/payments/webhook/"

PERMISSIONS_URL = f"{BASE_URL}/api/permissions/"
ROLES_URL = f"{BASE_URL}/api/roles/"

PASSWORD = "123456"
ADMIN_USERNAME = "loadadmin"
ADMIN_PASSWORD = "admin123"

PRODUCT_COUNT = 5
PRODUCT_NAMES = [f"Load Test Product {i}" for i in range(1, PRODUCT_COUNT + 1)]
CATEGORY_NAME = "Load Test Category"

TOTAL_USERS = 200
CONCURRENCY = 20
RUN_ID = int(time.time())
TIMEOUT = 20

ITEMS_PER_ORDER_RANGE = (1, 3)
QUANTITY_RANGE = (1, 3)

SEED_ENABLE = True
SEED_CATEGORY_COUNT = 100
SEED_PRODUCTS_PER_CATEGORY = 50
SEED_PRODUCTS_NO_CATEGORY = 500
SEED_BATCH_SIZE = 1000


def ensure_admin_user():
    User = get_user_model()
    admin, _ = User.objects.get_or_create(username=ADMIN_USERNAME)
    admin.is_staff = True
    admin.is_superuser = True
    admin.set_password(ADMIN_PASSWORD)
    admin.save(update_fields=["is_staff", "is_superuser", "password"])


def seed_bulk_data():
    if not SEED_ENABLE:
        return

    category_prefix = f"Seed Category {RUN_ID}"
    product_prefix = f"Seed Product {RUN_ID}"

    categories = [
        Category(name=f"{category_prefix} {i}")
        for i in range(1, SEED_CATEGORY_COUNT + 1)
    ]
    Category.objects.bulk_create(categories, batch_size=SEED_BATCH_SIZE)

    categories = list(Category.objects.filter(name__startswith=category_prefix))
    products = []

    for category in categories:
        for index in range(1, SEED_PRODUCTS_PER_CATEGORY + 1):
            products.append(
                Product(
                    name=f"{product_prefix} {category.id}-{index}",
                    price=1000 + (index * 10),
                    stock=1000,
                    category=category,
                )
            )

    for index in range(1, SEED_PRODUCTS_NO_CATEGORY + 1):
        products.append(
            Product(
                name=f"{product_prefix} NoCat {index}",
                price=800 + (index * 5),
                stock=1000,
            )
        )

    if products:
        Product.objects.bulk_create(products, batch_size=SEED_BATCH_SIZE)


def sign_webhook_payload(payload, timestamp, secret):
    payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    message = f"{timestamp}.{payload_str}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def request_json(session, method, url, **kwargs):
    try:
        async with session.request(method, url, **kwargs) as resp:
            try:
                data = await resp.json()
            except Exception:
                data = await resp.text()
            return resp.status, data
    except Exception as exc:
        return "error", {"error": str(exc)}


async def login(session, username, password):
    return await request_json(
        session,
        "POST",
        LOGIN_URL,
        json={"username": username, "password": password},
    )


async def ensure_category(session, admin_headers, results):
    status, data = await request_json(session, "GET", CATEGORIES_URL, headers=admin_headers)
    results.append(("categories_list_admin", status))
    if status != 200:
        raise RuntimeError(f"Failed to list categories: {data}")

    existing = next((item for item in data if item.get("name") == CATEGORY_NAME), None)
    if existing:
        return existing["id"]

    status, data = await request_json(
        session,
        "POST",
        CATEGORIES_URL,
        headers=admin_headers,
        json={"name": CATEGORY_NAME},
    )
    results.append(("categories_create_admin", status))
    if status != 201:
        raise RuntimeError(f"Failed to create category: {data}")
    return data["id"]


async def ensure_products(session, admin_headers, category_id, stock_needed, results):
    status, data = await request_json(session, "GET", PRODUCTS_URL, headers=admin_headers)
    results.append(("products_list_admin", status))
    if status != 200:
        raise RuntimeError(f"Failed to list products: {data}")

    existing = {item.get("name"): item for item in data}
    product_ids = []

    for index, name in enumerate(PRODUCT_NAMES, start=1):
        product = existing.get(name)
        if product is None:
            payload = {
                "name": name,
                "price": 1000 + index * 100,
                "stock": stock_needed,
                "category": category_id,
            }
            status, data = await request_json(
                session,
                "POST",
                PRODUCTS_URL,
                headers=admin_headers,
                json=payload,
            )
            results.append(("products_create_admin", status))
            if status != 201:
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
                "category": category_id,
            }
            status, data = await request_json(
                session,
                "PUT",
                f"{PRODUCTS_URL}{product_id}/",
                headers=admin_headers,
                json=payload,
            )
            results.append(("products_update_admin", status))
            if status != 200:
                raise RuntimeError(f"Failed to update product stock: {data}")

    return product_ids


async def create_and_cleanup_temp_resources(session, admin_headers, category_id, results):
    temp_category_name = f"Load Test Temp Category {RUN_ID}"
    status, data = await request_json(
        session,
        "POST",
        CATEGORIES_URL,
        headers=admin_headers,
        json={"name": temp_category_name},
    )
    results.append(("categories_create_temp", status))
    if status != 201:
        raise RuntimeError(f"Failed to create temp category: {data}")
    temp_category_id = data["id"]

    updated_category_name = f"{temp_category_name} Updated"
    status, data = await request_json(
        session,
        "PUT",
        f"{CATEGORIES_URL}{temp_category_id}/",
        headers=admin_headers,
        json={"name": updated_category_name},
    )
    results.append(("categories_update_temp", status))
    if status != 200:
        raise RuntimeError(f"Failed to update temp category: {data}")

    temp_product_name = f"Load Test Temp Product {RUN_ID}"
    status, data = await request_json(
        session,
        "POST",
        PRODUCTS_URL,
        headers=admin_headers,
        json={
            "name": temp_product_name,
            "price": 1500,
            "stock": 10,
            "category": category_id,
        },
    )
    results.append(("products_create_temp", status))
    if status != 201:
        raise RuntimeError(f"Failed to create temp product: {data}")
    temp_product_id = data["id"]

    status, data = await request_json(
        session,
        "PUT",
        f"{PRODUCTS_URL}{temp_product_id}/",
        headers=admin_headers,
        json={
            "name": f"{temp_product_name} Updated",
            "price": 2000,
            "stock": 15,
            "category": category_id,
        },
    )
    results.append(("products_update_temp", status))
    if status != 200:
        raise RuntimeError(f"Failed to update temp product: {data}")

    status, _ = await request_json(
        session,
        "DELETE",
        f"{PRODUCTS_URL}{temp_product_id}/",
        headers=admin_headers,
    )
    results.append(("products_delete_temp", status))

    status, _ = await request_json(
        session,
        "DELETE",
        f"{CATEGORIES_URL}{temp_category_id}/",
        headers=admin_headers,
    )
    results.append(("categories_delete_temp", status))


async def ensure_permission(session, admin_headers, codename, name, results):
    status, perms = await request_json(session, "GET", PERMISSIONS_URL, headers=admin_headers)
    results.append(("permissions_list", status))
    if status != 200:
        raise RuntimeError(f"Failed to list permissions: {perms}")

    permission = next((p for p in perms if p.get("codename") == codename), None)
    if permission:
        return permission["id"], False

    status, permission = await request_json(
        session,
        "POST",
        PERMISSIONS_URL,
        headers=admin_headers,
        json={"codename": codename, "name": name},
    )
    results.append(("permissions_create", status))
    if status != 201:
        raise RuntimeError(f"Failed to create permission: {permission}")

    return permission["id"], True


async def update_permission(session, admin_headers, perm_id, codename, name, results):
    status, data = await request_json(
        session,
        "PUT",
        f"{PERMISSIONS_URL}{perm_id}/",
        headers=admin_headers,
        json={"codename": codename, "name": name},
    )
    results.append(("permissions_update", status))
    if status != 200:
        raise RuntimeError(f"Failed to update permission: {data}")


async def ensure_role(session, admin_headers, name, permission_ids, results):
    status, roles = await request_json(session, "GET", ROLES_URL, headers=admin_headers)
    results.append(("roles_list", status))
    if status != 200:
        raise RuntimeError(f"Failed to list roles: {roles}")

    role = next((r for r in roles if r.get("name") == name), None)
    if role:
        return role["id"], False

    status, role = await request_json(
        session,
        "POST",
        ROLES_URL,
        headers=admin_headers,
        json={"name": name, "permissions": permission_ids},
    )
    results.append(("roles_create", status))
    if status != 201:
        raise RuntimeError(f"Failed to create role: {role}")

    return role["id"], True


async def update_role(session, admin_headers, role_id, name, permission_ids, results):
    status, data = await request_json(
        session,
        "PUT",
        f"{ROLES_URL}{role_id}/",
        headers=admin_headers,
        json={"name": name, "permissions": permission_ids},
    )
    results.append(("roles_update", status))
    if status != 200:
        raise RuntimeError(f"Failed to update role: {data}")


async def user_flow(
    session,
    sem,
    username,
    product_ids,
    category_id,
    admin_headers,
    role_id,
    do_admin,
):
    results = []
    meta = {"user_id": None}

    async with sem:
        status, _ = await request_json(
            session,
            "POST",
            REGISTER_URL,
            json={"username": username, "password": PASSWORD},
        )
        results.append(("auth_register", status))

        status, data = await login(session, username, PASSWORD)
        results.append(("auth_login", status))
        if status != 200 or "access" not in data:
            return results, meta

        token = data["access"]
        headers = {"Authorization": f"Bearer {token}"}

        status, me_data = await request_json(session, "GET", ME_URL, headers=headers)
        results.append(("auth_me", status))
        user_id = me_data.get("id") if status == 200 else None
        meta["user_id"] = user_id

        if do_admin and user_id:
            role_assign_url = f"{ROLES_URL}{role_id}/users/{user_id}/"
            status, _ = await request_json(session, "POST", role_assign_url, headers=admin_headers)
            results.append(("roles_assign", status))

        status, _ = await request_json(session, "GET", CATEGORIES_URL, headers=headers)
        results.append(("categories_list", status))

        status, _ = await request_json(session, "GET", PRODUCTS_URL, headers=headers)
        results.append(("products_list", status))

        status, _ = await request_json(
            session,
            "GET",
            f"{PRODUCTS_URL}?search=Load",
            headers=headers,
        )
        results.append(("products_search", status))

        status, _ = await request_json(
            session,
            "GET",
            f"{PRODUCTS_URL}?category={category_id}",
            headers=headers,
        )
        results.append(("products_filter", status))

        status, _ = await request_json(
            session,
            "GET",
            PRODUCT_STATS_URL,
            headers=headers,
        )
        results.append(("products_stats", status))

        product_id = random.choice(product_ids)
        status, _ = await request_json(
            session,
            "GET",
            f"{PRODUCTS_URL}{product_id}/",
            headers=headers,
        )
        results.append(("products_detail", status))

        item_count = random.randint(*ITEMS_PER_ORDER_RANGE)
        picked_ids = random.sample(product_ids, k=item_count)
        cart_item_ids = []
        for pid in picked_ids:
            payload = {
                "product_id": pid,
                "quantity": random.randint(*QUANTITY_RANGE),
            }
            status, data = await request_json(
                session,
                "POST",
                CART_URL,
                headers=headers,
                json=payload,
            )
            results.append(("cart_add", status))
            if status == 201:
                cart_item_ids.append(data.get("id"))

        status, _ = await request_json(session, "GET", CART_URL, headers=headers)
        results.append(("cart_get", status))

        if cart_item_ids:
            payload = {"quantity": random.randint(*QUANTITY_RANGE)}
            status, _ = await request_json(
                session,
                "PUT",
                f"{CART_URL}items/{cart_item_ids[0]}/",
                headers=headers,
                json=payload,
            )
            results.append(("cart_update", status))

        if len(cart_item_ids) > 1:
            status, _ = await request_json(
                session,
                "DELETE",
                f"{CART_URL}items/{cart_item_ids[-1]}/",
                headers=headers,
            )
            results.append(("cart_delete", status))

        status, order_data = await request_json(session, "POST", ORDERS_URL, headers=headers)
        results.append(("orders_create", status))
        order_id = order_data.get("id") if status == 201 else None

        status, _ = await request_json(session, "GET", ORDERS_URL, headers=headers)
        results.append(("orders_list", status))

        if order_id:
            status, _ = await request_json(
                session,
                "GET",
                f"{ORDERS_URL}{order_id}/",
                headers=headers,
            )
            results.append(("orders_detail", status))

            status, _ = await request_json(
                session,
                "POST",
                f"{ORDERS_URL}{order_id}/checkout/",
                headers=headers,
            )
            results.append(("orders_checkout_alias", status))

        payment_id = None
        transaction_id = None
        if order_id:
            status, pay_data = await request_json(
                session,
                "POST",
                PAYMENTS_CREATE_URL,
                headers=headers,
                json={"order_id": order_id, "provider": "vnpay"},
            )
            results.append(("payments_create", status))
            if status == 201:
                payment_id = pay_data.get("payment_id")
                transaction_id = pay_data.get("transaction_id")

        if payment_id:
            status, _ = await request_json(
                session,
                "GET",
                f"{PAYMENTS_STATUS_URL}{payment_id}/status/",
                headers=headers,
            )
            results.append(("payments_status_before", status))

        if transaction_id and order_id:
            webhook_payload = {
                "transaction_id": transaction_id,
                "order_id": order_id,
                "status": "paid",
                "provider": "vnpay",
            }
            timestamp = str(int(time.time()))
            secret = os.getenv("PAYMENT_WEBHOOK_SECRET", "dev-webhook-secret")
            signature = sign_webhook_payload(webhook_payload, timestamp, secret)
            webhook_headers = {
                "X-Webhook-Timestamp": timestamp,
                "X-Webhook-Signature": signature,
            }
            status, _ = await request_json(
                session,
                "POST",
                PAYMENTS_WEBHOOK_URL,
                json=webhook_payload,
                headers=webhook_headers,
            )
            results.append(("payments_webhook", status))

        if payment_id:
            status, _ = await request_json(
                session,
                "GET",
                f"{PAYMENTS_STATUS_URL}{payment_id}/status/",
                headers=headers,
            )
            results.append(("payments_status_after", status))

        if do_admin and order_id:
            status, _ = await request_json(
                session,
                "PATCH",
                f"{ORDERS_URL}{order_id}/status/",
                headers=headers,
                json={"status": "shipped"},
            )
            results.append(("orders_status_shipped_user", status))

            status, _ = await request_json(
                session,
                "PATCH",
                f"{ORDERS_URL}{order_id}/status/",
                headers=admin_headers,
                json={"status": "completed"},
            )
            results.append(("orders_status_completed_admin", status))

    return results, meta


async def main():
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    sem = asyncio.Semaphore(CONCURRENCY)
    start = time.time()

    usernames = [f"loaduser_{RUN_ID}_{i}" for i in range(TOTAL_USERS)]
    admin_results = []

    async with aiohttp.ClientSession(timeout=timeout) as session:
        status, _ = await request_json(session, "GET", HELLO_URL)
        admin_results.append(("hello", status))
        if status != 200:
            raise RuntimeError("Hello endpoint failed.")

        status, data = await login(session, ADMIN_USERNAME, ADMIN_PASSWORD)
        admin_results.append(("auth_login_admin", status))
        if status != 200 or "access" not in data:
            raise RuntimeError(f"Admin login failed: {data}")
        admin_headers = {"Authorization": f"Bearer {data['access']}"}

        status, admin_create = await request_json(
            session,
            "POST",
            REGISTER_ADMIN_URL,
            headers=admin_headers,
            json={"username": f"loadadmin_{RUN_ID}", "password": ADMIN_PASSWORD},
        )
        admin_results.append(("auth_register_admin", status))

        category_id = await ensure_category(session, admin_headers, admin_results)
        product_ids = await ensure_products(
            session,
            admin_headers,
            category_id,
            TOTAL_USERS * max(QUANTITY_RANGE) * 3,
            admin_results,
        )
        await create_and_cleanup_temp_resources(session, admin_headers, category_id, admin_results)

        perm_id, perm_created = await ensure_permission(
            session,
            admin_headers,
            codename="update_order_status",
            name="Update order status",
            results=admin_results,
        )
        if perm_created:
            await update_permission(
                session,
                admin_headers,
                perm_id,
                codename="update_order_status",
                name="Update order status (load test)",
                results=admin_results,
            )

        temp_perm_id, temp_perm_created = await ensure_permission(
            session,
            admin_headers,
            codename=f"load_test_permission_{RUN_ID}",
            name="Load Test Permission",
            results=admin_results,
        )
        if temp_perm_created:
            await update_permission(
                session,
                admin_headers,
                temp_perm_id,
                codename=f"load_test_permission_{RUN_ID}",
                name="Load Test Permission Updated",
                results=admin_results,
            )

        role_name = f"load_test_role_{RUN_ID}"
        role_id, role_created = await ensure_role(
            session,
            admin_headers,
            name=role_name,
            permission_ids=[perm_id],
            results=admin_results,
        )
        if role_created:
            await update_role(
                session,
                admin_headers,
                role_id,
                name=f"{role_name}_updated",
                permission_ids=[perm_id],
                results=admin_results,
            )

        tasks = []
        for index, username in enumerate(usernames):
            do_admin = index == 0
            tasks.append(user_flow(
                session,
                sem,
                username,
                product_ids,
                category_id,
                admin_headers,
                role_id=role_id,
                do_admin=do_admin,
            ))

        results = await asyncio.gather(*tasks)

        first_user_id = None
        for _, meta in results:
            if meta.get("user_id"):
                first_user_id = meta["user_id"]
                break

        if first_user_id:
            status, _ = await request_json(
                session,
                "DELETE",
                f"{ROLES_URL}{role_id}/users/{first_user_id}/",
                headers=admin_headers,
            )
            admin_results.append(("roles_unassign", status))

        if role_created:
            status, _ = await request_json(
                session,
                "DELETE",
                f"{ROLES_URL}{role_id}/",
                headers=admin_headers,
            )
            admin_results.append(("roles_delete", status))

        if temp_perm_created:
            status, _ = await request_json(
                session,
                "DELETE",
                f"{PERMISSIONS_URL}{temp_perm_id}/",
                headers=admin_headers,
            )
            admin_results.append(("permissions_delete_temp", status))

        if perm_created:
            status, _ = await request_json(
                session,
                "DELETE",
                f"{PERMISSIONS_URL}{perm_id}/",
                headers=admin_headers,
            )
            admin_results.append(("permissions_delete_update_order_status", status))

    duration = time.time() - start

    counters = defaultdict(Counter)
    for key, status in admin_results:
        counters[key][status] += 1
    for result, _ in results:
        for key, status in result:
            counters[key][status] += 1

    print("===== FULL SYSTEM LOAD TEST =====")
    print(f"Total users: {TOTAL_USERS}")
    print(f"Concurrency: {CONCURRENCY}")
    print(f"Duration: {duration:.2f}s")
    print(f"RPS: {TOTAL_USERS / duration:.2f}")
    print("Status breakdown:")
    for key in sorted(counters.keys()):
        print(f"- {key}: {dict(counters[key])}")


if __name__ == "__main__":
    ensure_admin_user()
    seed_bulk_data()
    asyncio.run(main())

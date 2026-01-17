import asyncio
import gc
import hashlib
import hmac
import json
import os
import psutil
import random
import re
import time
from collections import Counter, defaultdict
from asgiref.sync import sync_to_async

import aiohttp

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
import django

django.setup()

from django.contrib.auth import get_user_model
from django.db import connection

from api.models import Category, Product, Wishlist

BASE_URL = "http://127.0.0.1:8000"

HELLO_URL = f"{BASE_URL}/api/hello/"
LOGIN_URL = f"{BASE_URL}/api/auth/login/"
REGISTER_URL = f"{BASE_URL}/api/auth/register/"
REGISTER_ADMIN_URL = f"{BASE_URL}/api/auth/register-admin/"
ME_URL = f"{BASE_URL}/api/auth/me/"

PRODUCTS_URL = f"{BASE_URL}/api/products/"
PRODUCT_STATS_URL = f"{BASE_URL}/api/products/statistics/"
CATEGORIES_URL = f"{BASE_URL}/api/categories/"
WISHLIST_URL = f"{BASE_URL}/api/wishlist/"

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

def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


TOTAL_USERS = env_int("LOAD_TOTAL_USERS", 200)
CONCURRENCY = env_int("LOAD_CONCURRENCY", 20)
RUN_ID = int(time.time())
TIMEOUT = env_float("LOAD_TIMEOUT", 5)  # Reduced timeout for faster failure detection

ITEMS_PER_ORDER_RANGE = (1, 3)
QUANTITY_RANGE = (1, 3)

SEED_ENABLE = True
SEED_CATEGORY_COUNT = env_int("LOAD_SEED_CATEGORY_COUNT", 100)
SEED_PRODUCTS_PER_CATEGORY = env_int("LOAD_SEED_PRODUCTS_PER_CATEGORY", 50)
SEED_PRODUCTS_NO_CATEGORY = env_int("LOAD_SEED_PRODUCTS_NO_CATEGORY", 500)
SEED_BATCH_SIZE = env_int("LOAD_SEED_BATCH_SIZE", 1000)

# Optimized concurrency settings for better performance
REQUEST_CONCURRENCY = env_int("LOAD_REQUEST_CONCURRENCY", max(100, CONCURRENCY * 3))
WRITE_CONCURRENCY = env_int("LOAD_WRITE_CONCURRENCY", max(20, CONCURRENCY))
AUTH_CONCURRENCY = env_int("LOAD_AUTH_CONCURRENCY", max(10, CONCURRENCY // 2))
CONNECT_RETRIES = env_int("LOAD_CONNECT_RETRIES", 3)  # More retries
CONNECT_RETRY_BACKOFF = env_float("LOAD_CONNECT_RETRY_BACKOFF", 0.1)  # Faster backoff
READ_RETRIES = env_int("LOAD_READ_RETRIES", 2)  # More read retries
RETRY_BACKOFF_BASE = env_float("LOAD_RETRY_BACKOFF", 0.1)  # Faster retry backoff
RETRY_STATUS_CODES = {429, 502, 503, 504, 500}  # Include 500 errors
ENABLE_WISHLIST_FLOW = True
STARTUP_JITTER = env_float("LOAD_STARTUP_JITTER", 0.5)
RAMP_UP_SECONDS = env_float("LOAD_RAMP_UP_SECONDS", 20)
LOG_ERROR_SAMPLES = True
ERROR_SAMPLE_LIMIT = env_int("LOAD_ERROR_SAMPLE_LIMIT", 3)
ERROR_BODY_LIMIT = env_int("LOAD_ERROR_BODY_LIMIT", 400)

READ_BURST = env_int("LOAD_READ_BURST", 2)
CART_ADD_BURST = env_int("LOAD_CART_ADD_BURST", 1)
USE_ALL_PRODUCTS = env_bool("LOAD_USE_ALL_PRODUCTS", True)
MIN_PRODUCT_STOCK = env_int("LOAD_MIN_PRODUCT_STOCK", 1)

REQUEST_SEM = None
WRITE_SEM = None
AUTH_SEM = None
ERROR_SAMPLES = defaultdict(list)

# Circuit breaker for connection failures
CIRCUIT_BREAKER_FAILURES = 0
CIRCUIT_BREAKER_THRESHOLD = 10  # Open circuit after this many failures
CIRCUIT_BREAKER_TIMEOUT = 30    # Seconds to wait before trying again
CIRCUIT_BREAKER_LAST_FAILURE = 0

# Memory optimization settings
MEMORY_CHECK_INTERVAL = 30  # Check memory every 30 seconds
MEMORY_WARNING_THRESHOLD = 80  # Warn at 80% memory usage
LAST_MEMORY_CHECK = 0
MEMORY_STATS = {"peak_mb": 0, "current_mb": 0, "warnings": 0}


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


def ensure_required_tables():
    try:
        tables = set(connection.introspection.table_names())
    except Exception as exc:
        print(f"Table check failed: {exc}")
        return False

    required = {Wishlist._meta.db_table}
    missing = sorted(required - tables)
    if missing:
        print("Missing tables:", ", ".join(missing))
        print("Run migrations before the load test (python manage.py migrate).")
        return False
    return True


def sign_webhook_payload(payload, timestamp, secret):
    payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    message = f"{timestamp}.{payload_str}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def _do_request(session, method, url, **kwargs):
    async with session.request(method, url, **kwargs) as resp:
        try:
            data = await resp.json()
        except Exception:
            data = await resp.text()
        return resp.status, data


def normalize_error_data(data):
    if isinstance(data, (dict, list)):
        text = json.dumps(data, ensure_ascii=True)
    else:
        text = str(data)
    if len(text) > ERROR_BODY_LIMIT:
        return f"{text[:ERROR_BODY_LIMIT]}...[truncated]"
    return text


def normalize_error_url(url):
    base = url.split("?", 1)[0]
    return re.sub(r"/\d+/", "/{id}/", base)


def check_memory_usage():
    """Monitor memory usage and trigger garbage collection if needed."""
    global LAST_MEMORY_CHECK, MEMORY_STATS

    current_time = time.time()
    if current_time - LAST_MEMORY_CHECK < MEMORY_CHECK_INTERVAL:
        return

    LAST_MEMORY_CHECK = current_time

    try:
        process = psutil.Process()
        memory_percent = process.memory_percent()
        memory_mb = process.memory_info().rss / 1024 / 1024

        MEMORY_STATS["current_mb"] = memory_mb
        MEMORY_STATS["peak_mb"] = max(MEMORY_STATS["peak_mb"], memory_mb)

        if memory_percent > MEMORY_WARNING_THRESHOLD:
            MEMORY_STATS["warnings"] += 1
            print(f"High memory usage detected: {memory_percent:.1f}% ({memory_mb:.1f} MB)")
            # Force garbage collection when memory is high
            gc.collect()
            print(f"  -> Garbage collection completed")

    except Exception as exc:
        print(f"Memory monitoring error: {exc}")


def optimize_memory():
    """Memory optimization strategies for load testing."""
    # Clear any cached objects that might be accumulating
    if hasattr(gc, 'get_objects'):
        # Force cleanup of circular references
        gc.collect()

    # Clear any large caches if they exist
    try:
        from django.core.cache import cache
        cache.clear()
    except Exception:
        pass


def record_error(method, url, status, data):
    if not LOG_ERROR_SAMPLES:
        return
    if status != "error" and not (isinstance(status, int) and status >= 400):
        return
    key = f"{method.upper()} {normalize_error_url(url)}"
    samples = ERROR_SAMPLES[key]
    if len(samples) >= ERROR_SAMPLE_LIMIT:
        return
    samples.append(normalize_error_data(data))


CLIENT_OS_ERROR = getattr(aiohttp, "ClientOSError", OSError)

CONNECT_ERROR_TYPES = (
    aiohttp.ClientConnectorError,
    aiohttp.ServerDisconnectedError,
    CLIENT_OS_ERROR,
    asyncio.TimeoutError,
    ConnectionResetError,
)


def is_connect_error(exc):
    return isinstance(exc, CONNECT_ERROR_TYPES)


def select_semaphore(method, url):
    if AUTH_SEM is not None and "/api/auth/" in url:
        return AUTH_SEM
    if method not in {"GET", "HEAD"} and WRITE_SEM is not None:
        return WRITE_SEM
    return REQUEST_SEM


async def request_json(session, method, url, **kwargs):
    global CIRCUIT_BREAKER_FAILURES, CIRCUIT_BREAKER_LAST_FAILURE

    # Memory check
    check_memory_usage()

    # Circuit breaker check
    current_time = time.time()
    if CIRCUIT_BREAKER_FAILURES >= CIRCUIT_BREAKER_THRESHOLD:
        if current_time - CIRCUIT_BREAKER_LAST_FAILURE < CIRCUIT_BREAKER_TIMEOUT:
            # Circuit is open, fail fast
            error_data = {"error": "Circuit breaker open - too many connection failures"}
            record_error(method, url, "error", error_data)
            return "error", error_data
        else:
            # Reset circuit breaker
            CIRCUIT_BREAKER_FAILURES = 0

    read_retries = READ_RETRIES if method in {"GET", "HEAD"} else 0
    read_attempts = 0
    connect_attempts = 0
    max_total_attempts = max(CONNECT_RETRIES + read_retries + 1, 5)  # Ensure minimum attempts
    total_attempts = 0

    while total_attempts < max_total_attempts:
        total_attempts += 1
        try:
            sem = select_semaphore(method, url)
            if sem is None:
                status, data = await _do_request(session, method, url, **kwargs)
            else:
                async with sem:
                    status, data = await _do_request(session, method, url, **kwargs)
        except Exception as exc:
            if is_connect_error(exc) and connect_attempts < CONNECT_RETRIES:
                connect_attempts += 1
                # Exponential backoff with jitter for connection errors
                backoff_time = CONNECT_RETRY_BACKOFF * (2 ** (connect_attempts - 1))
                backoff_time += random.uniform(0, min(backoff_time * 0.1, 0.1))  # Add jitter
                await asyncio.sleep(backoff_time)
                continue

            # Circuit breaker: count connection failures
            if is_connect_error(exc):
                CIRCUIT_BREAKER_FAILURES += 1
                CIRCUIT_BREAKER_LAST_FAILURE = current_time

            error_data = {"error": str(exc)}
            record_error(method, url, "error", error_data)
            return "error", error_data

        # Success case
        if status < 400:
            record_error(method, url, status, data)
            return status, data

        # Retry on specific status codes
        if status in RETRY_STATUS_CODES and read_attempts < read_retries:
            read_attempts += 1
            # Exponential backoff with jitter for server errors
            backoff_time = RETRY_BACKOFF_BASE * (2 ** (read_attempts - 1))
            backoff_time += random.uniform(0, min(backoff_time * 0.1, 0.1))  # Add jitter
            await asyncio.sleep(backoff_time)
            continue

        # Final failure
        record_error(method, url, status, data)
        return status, data


def build_requests(label, method, url, count, **kwargs):
    return [(label, method, url, dict(kwargs)) for _ in range(count)]


async def run_parallel(session, request_specs, results):
    if not request_specs:
        return []
    tasks = [
        request_json(session, method, url, **kwargs)
        for _, method, url, kwargs in request_specs
    ]
    responses = await asyncio.gather(*tasks)
    for (label, _, _, _), (status, _) in zip(request_specs, responses):
        results.append((label, status))
    return responses


async def login(session, username, password):
    return await request_json(
        session,
        "POST",
        LOGIN_URL,
        json={"username": username, "password": password},
    )


async def login_admin(session, results, label="auth_login_admin", raise_on_fail=True):
    status, data = await login(session, ADMIN_USERNAME, ADMIN_PASSWORD)
    results.append((label, status))
    token = data.get("access") if isinstance(data, dict) else None
    if status != 200 or not token:
        if raise_on_fail:
            raise RuntimeError(f"Admin login failed: {data}")
        return None
    return {"Authorization": f"Bearer {token}"}


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


def load_product_ids(min_stock):
    queryset = Product.objects.all()
    if min_stock is not None:
        queryset = queryset.filter(stock__gte=min_stock)
    return list(queryset.values_list("id", flat=True))


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
    start_delay=0.0,
):
    results = []
    meta = {"user_id": None}

    if start_delay:
        await asyncio.sleep(start_delay)
    if STARTUP_JITTER:
        await asyncio.sleep(random.uniform(0, STARTUP_JITTER))

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

        product_id = random.choice(product_ids)
        read_requests = []
        read_requests += build_requests("categories_list", "GET", CATEGORIES_URL, READ_BURST, headers=headers)
        read_requests += build_requests("products_list", "GET", PRODUCTS_URL, READ_BURST, headers=headers)
        read_requests += build_requests(
            "products_search",
            "GET",
            f"{PRODUCTS_URL}?search=Load",
            READ_BURST,
            headers=headers,
        )
        read_requests += build_requests(
            "products_filter",
            "GET",
            f"{PRODUCTS_URL}?category={category_id}",
            READ_BURST,
            headers=headers,
        )
        read_requests += build_requests("products_stats", "GET", PRODUCT_STATS_URL, READ_BURST, headers=headers)
        read_requests += build_requests(
            "products_detail",
            "GET",
            f"{PRODUCTS_URL}{product_id}/",
            READ_BURST,
            headers=headers,
        )
        await run_parallel(session, read_requests, results)

        if ENABLE_WISHLIST_FLOW:
            status, _ = await request_json(
                session,
                "POST",
                WISHLIST_URL,
                headers=headers,
                json={"product_id": product_id},
            )
            results.append(("wishlist_add", status))
            if status == 201:
                wishlist_requests = build_requests(
                    "wishlist_list",
                    "GET",
                    WISHLIST_URL,
                    READ_BURST,
                    headers=headers,
                )
                await run_parallel(session, wishlist_requests, results)

                status, _ = await request_json(
                    session,
                    "DELETE",
                    f"{WISHLIST_URL}{product_id}/",
                    headers=headers,
                )
                results.append(("wishlist_delete", status))

        item_count = random.randint(*ITEMS_PER_ORDER_RANGE)
        picked_ids = random.sample(product_ids, k=item_count)
        cart_item_ids = []
        cart_add_requests = []
        for pid in picked_ids:
            for _ in range(CART_ADD_BURST):
                payload = {
                    "product_id": pid,
                    "quantity": random.randint(*QUANTITY_RANGE),
                }
                cart_add_requests.append(
                    ("cart_add", "POST", CART_URL, {"headers": headers, "json": payload})
                )
        cart_add_responses = await run_parallel(session, cart_add_requests, results)
        for status, data in cart_add_responses:
            if status == 201 and isinstance(data, dict):
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

    global REQUEST_SEM, WRITE_SEM, AUTH_SEM
    REQUEST_SEM = asyncio.Semaphore(max(1, REQUEST_CONCURRENCY))
    if WRITE_CONCURRENCY > 0:
        WRITE_SEM = asyncio.Semaphore(max(1, WRITE_CONCURRENCY))
    if AUTH_CONCURRENCY > 0:
        AUTH_SEM = asyncio.Semaphore(max(1, AUTH_CONCURRENCY))

    # Configure connector with optimized settings for high concurrency
    connector = aiohttp.TCPConnector(
        limit=REQUEST_CONCURRENCY,           # Total connection limit
        limit_per_host=REQUEST_CONCURRENCY // 2,  # Per-host limit
        ttl_dns_cache=300,                   # DNS cache TTL
        use_dns_cache=True,                  # Enable DNS caching
        keepalive_timeout=60,                # Keep connections alive longer
        enable_cleanup_closed=True,          # Clean up closed connections
        force_close=False,                   # Keep connections open when possible
    )

    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        headers={"Connection": "keep-alive"}  # Enable keep-alive by default
    ) as session:
        status, _ = await request_json(session, "GET", HELLO_URL)
        admin_results.append(("hello", status))
        if status != 200:
            raise RuntimeError("Hello endpoint failed.")

        admin_headers = await login_admin(session, admin_results)

        status, admin_create = await request_json(
            session,
            "POST",
            REGISTER_ADMIN_URL,
            headers=admin_headers,
            json={"username": f"loadadmin_{RUN_ID}", "password": ADMIN_PASSWORD},
        )
        admin_results.append(("auth_register_admin", status))

        category_id = await ensure_category(session, admin_headers, admin_results)
        stock_needed = (
            TOTAL_USERS
            * max(ITEMS_PER_ORDER_RANGE)
            * max(QUANTITY_RANGE)
            * CART_ADD_BURST
        )
        product_ids = await ensure_products(
            session,
            admin_headers,
            category_id,
            stock_needed,
            admin_results,
        )
        if USE_ALL_PRODUCTS:
            all_product_ids = await sync_to_async(
                load_product_ids,
                thread_sensitive=True,
            )(MIN_PRODUCT_STOCK)
            if all_product_ids:
                product_ids = all_product_ids
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
        ramp_step = max(0.0, RAMP_UP_SECONDS) / max(1, TOTAL_USERS)
        for index, username in enumerate(usernames):
            do_admin = index == 0
            start_delay = ramp_step * index
            tasks.append(user_flow(
                session,
                sem,
                username,
                product_ids,
                category_id,
                admin_headers,
                role_id=role_id,
                do_admin=do_admin,
                start_delay=start_delay,
            ))

        results = await asyncio.gather(*tasks)

        refreshed_headers = await login_admin(
            session,
            admin_results,
            label="auth_login_admin_cleanup",
            raise_on_fail=False,
        )
        if refreshed_headers:
            admin_headers = refreshed_headers

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

    # Final memory optimization
    optimize_memory()

    counters = defaultdict(Counter)
    for key, status in admin_results:
        counters[key][status] += 1
    for result, _ in results:
        for key, status in result:
            counters[key][status] += 1

    # Calculate success rates
    total_requests = sum(sum(counter.values()) for counter in counters.values())
    successful_requests = sum(
        counter[status] for counter in counters.values()
        for status in counter.keys() if status in {200, 201, 204}
    )
    success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0

    print("===== FULL SYSTEM LOAD TEST =====")
    print(f"Total users: {TOTAL_USERS}")
    print(f"Concurrency: {CONCURRENCY}")
    print(f"Duration: {duration:.2f}s")
    print(f"RPS: {total_requests / duration:.2f}")
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Memory peak: {MEMORY_STATS['peak_mb']:.1f} MB")
    print(f"Memory warnings: {MEMORY_STATS['warnings']}")
    print("Status breakdown:")
    for key in sorted(counters.keys()):
        print(f"- {key}: {dict(counters[key])}")
    if LOG_ERROR_SAMPLES and ERROR_SAMPLES:
        print("Error samples:")
        for key in sorted(ERROR_SAMPLES.keys()):
            print(f"- {key}: {ERROR_SAMPLES[key]}")


if __name__ == "__main__":
    # Set load test mode for optimized settings
    os.environ.setdefault('LOAD_TEST_MODE', 'true')
    os.environ.setdefault('DEBUG', 'false')

    print("Starting optimized load test...")
    print(f"Settings: CONCURRENCY={CONCURRENCY}, TOTAL_USERS={TOTAL_USERS}")
    print(f"Database: {os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}")

    ensure_admin_user()
    seed_bulk_data()
    if not ensure_required_tables():
        raise SystemExit(1)
    asyncio.run(main())

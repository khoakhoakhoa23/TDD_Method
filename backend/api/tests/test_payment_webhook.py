import hashlib
import hmac
import json
import time
import uuid

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APIClient

from api.models import Order, Payment


def sign_webhook_payload(payload, timestamp, secret):
    payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    message = f"{timestamp}.{payload_str}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def build_headers(payload, secret=None, timestamp=None):
    if secret is None:
        secret = settings.PAYMENT_WEBHOOK_SECRET
    if timestamp is None:
        timestamp = str(int(time.time()))
    signature = sign_webhook_payload(payload, timestamp, secret)
    return {
        "HTTP_X_WEBHOOK_TIMESTAMP": timestamp,
        "HTTP_X_WEBHOOK_SIGNATURE": signature,
    }


@pytest.mark.django_db
def test_payment_webhook_idempotent():
    user = User.objects.create_user("khoa", "pass123")
    order = Order.objects.create(user=user, total=100000)

    payment = Payment.objects.create(
        order=order,
        provider="vnpay",
        amount=100000
    )

    client = APIClient()

    payload = {
        "transaction_id": "TXN123",
        "order_id": order.id,
        "status": "paid"
    }

    headers = build_headers(payload)

    # webhook gọi lần 1
    r1 = client.post("/api/payments/webhook/", payload, format="json", **headers)
    assert r1.status_code == 200

    # webhook gọi lần 2 (retry)
    r2 = client.post("/api/payments/webhook/", payload, format="json", **headers)
    assert r2.status_code == 200

    payment.refresh_from_db()
    order.refresh_from_db()

    assert payment.status == "paid"
    assert order.status == "paid"

def test_payment_webhook_invalid_transaction():
    client = APIClient()

    payload = {
        "transaction_id": "INVALID_TXN",
        "order_id": 1,
        "status": "paid"
    }

    response = client.post(
        "/api/payments/webhook/",
        payload,
        format="json",
        **build_headers(payload),
    )
    assert response.status_code == 400

@pytest.mark.django_db
def test_payment_webhook_missing_fields():
    client = APIClient()

    payload = {
        "transaction_id": "TXN123",
        # "order_id" is missing
        "status": "paid"
    }

    response = client.post(
        "/api/payments/webhook/",
        payload,
        format="json",
        **build_headers(payload),
    )
    assert response.status_code == 400

@pytest.mark.django_db
def test_payment_webhook_missing_signature():
    client = APIClient()

    payload = {
        "transaction_id": "TXN123",
        "order_id": 1,
        "status": "paid"
    }

    response = client.post("/api/payments/webhook/", payload, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_payment_webhook_invalid_signature():
    client = APIClient()

    payload = {
        "transaction_id": "TXNEDGE1",
        "order_id": 1,
        "status": "paid"
    }

    response = client.post(
        "/api/payments/webhook/",
        payload,
        format="json",
        **build_headers(payload, secret="wrong-secret"),
    )
    assert response.status_code == 400


@pytest.mark.django_db
@override_settings(PAYMENT_WEBHOOK_TOLERANCE_SECONDS=1)
def test_payment_webhook_expired_timestamp():
    client = APIClient()

    payload = {
        "transaction_id": "TXNEDGE2",
        "order_id": 1,
        "status": "paid"
    }

    expired_timestamp = str(int(time.time()) - 10)
    response = client.post(
        "/api/payments/webhook/",
        payload,
        format="json",
        **build_headers(payload, timestamp=expired_timestamp),
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_payment_webhook_invalid_status():
    client = APIClient()

    payload = {
        "transaction_id": "TXNEDGE3",
        "order_id": 1,
        "status": "unknown"
    }

    response = client.post(
        "/api/payments/webhook/",
        payload,
        format="json",
        **build_headers(payload),
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_payment_webhook_invalid_provider():
    client = APIClient()

    payload = {
        "transaction_id": "TXNEDGE4",
        "order_id": 1,
        "status": "paid",
        "provider": "paypal"
    }

    response = client.post(
        "/api/payments/webhook/",
        payload,
        format="json",
        **build_headers(payload),
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_payment_webhook_order_not_found():
    client = APIClient()

    payload = {
        "transaction_id": "TXNEDGE5",
        "order_id": 9999,
        "status": "paid",
        "provider": "vnpay"
    }

    response = client.post(
        "/api/payments/webhook/",
        payload,
        format="json",
        **build_headers(payload),
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_payment_webhook_success_maps_to_paid():
    client = APIClient()

    user = User.objects.create_user("khoa", "pass123")
    order = Order.objects.create(user=user, total=100000)

    payload = {
        "transaction_id": "TXNEDGE6",
        "order_id": order.id,
        "status": "success",
        "provider": "vnpay"
    }

    response = client.post(
        "/api/payments/webhook/",
        payload,
        format="json",
        **build_headers(payload),
    )
    assert response.status_code == 200

    payment = Payment.objects.get(transaction_id="TXNEDGE6")
    order.refresh_from_db()
    assert payment.status == "paid"
    assert order.status == "paid"


@pytest.mark.django_db
def test_payment_webhook_conflict_paid_to_failed():
    client = APIClient()

    user = User.objects.create_user("khoa", "pass123")
    order = Order.objects.create(user=user, total=100000)
    Payment.objects.create(
        order=order,
        provider="vnpay",
        amount=100000,
        status="paid",
        transaction_id="TXNEDGE7",
    )

    payload = {
        "transaction_id": "TXNEDGE7",
        "order_id": order.id,
        "status": "failed",
        "provider": "vnpay"
    }

    response = client.post(
        "/api/payments/webhook/",
        payload,
        format="json",
        **build_headers(payload),
    )
    assert response.status_code == 409


@pytest.mark.django_db
def test_payment_webhook_conflict_failed_to_paid():
    client = APIClient()

    user = User.objects.create_user("khoa", "pass123")
    order = Order.objects.create(user=user, total=100000)
    Payment.objects.create(
        order=order,
        provider="vnpay",
        amount=100000,
        status="failed",
        transaction_id="TXNEDGE8",
    )

    payload = {
        "transaction_id": "TXNEDGE8",
        "order_id": order.id,
        "status": "paid",
        "provider": "vnpay"
    }

    response = client.post(
        "/api/payments/webhook/",
        payload,
        format="json",
        **build_headers(payload),
    )
    assert response.status_code == 409

@pytest.mark.django_db
def test_payment_webhook_get_not_allowed():
    client = APIClient()

    response = client.get("/api/payments/webhook/")

    assert response.status_code == 405
   

@pytest.mark.django_db
def test_checkout_requires_authentication():
    client = APIClient()
    response = client.post("/api/orders/1/checkout/")
    assert response.status_code == 401

 




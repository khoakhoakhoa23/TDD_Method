import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from api.models import Category, Product, Order, Payment


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

    # webhook gọi lần 1
    r1 = client.post("/api/payments/webhook/", payload, format="json")
    assert r1.status_code == 200

    # webhook gọi lần 2 (retry)
    r2 = client.post("/api/payments/webhook/", payload, format="json")
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

    response = client.post("/api/payments/webhook/", payload, format="json")
    assert response.status_code == 400

@pytest.mark.django_db
def test_payment_webhook_missing_fields():
    client = APIClient()

    payload = {
        "transaction_id": "TXN123",
        # "order_id" is missing
        "status": "paid"
    }

    response = client.post("/api/payments/webhook/", payload, format="json")
    assert response.status_code == 400

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

 




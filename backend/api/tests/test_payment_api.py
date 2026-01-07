import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from api.models import Category, Product, Order, Payment
@pytest.mark.django_db
def test_create_payment():
    client = APIClient()

    user = User.objects.create_user("khoa", "pass123")
    client.force_authenticate(user=user)

    order = Order.objects.create(user=user, total=100000)

    response = client.post("/api/payments/create/", {
        "order_id": order.id,
        "provider": "vnpay"
    })

    assert response.status_code == 201
    assert "transaction_id" in response.data

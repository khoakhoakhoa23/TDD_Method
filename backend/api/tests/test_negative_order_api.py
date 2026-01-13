import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from api.models import Category, Order, Product


@pytest.fixture
def auth_client(authenticated_client):
    return authenticated_client


@pytest.fixture
def order(user):
    return Order.objects.create(user=user, total=100000)


@pytest.fixture
def paid_order(user):
    return Order.objects.create(user=user, total=100000, status="paid")


@pytest.fixture
def out_of_stock_product():
    category = Category.objects.create(name="Out of stock")
    return Product.objects.create(
        name="Sold out",
        price=100000,
        stock=0,
        category=category
    )

@pytest.mark.django_db
def test_checkout_empty_cart(auth_client):
    res = auth_client.post("/api/orders/")
    assert res.status_code == 400
@pytest.mark.django_db
def test_pay_already_paid_order(auth_client, paid_order):
    res = auth_client.post(
        "/api/payments/create/",
        {"order_id": paid_order.id, "provider": "vnpay"},
        format="json"
    )
    assert res.status_code == 400
@pytest.mark.django_db
def test_user_cannot_update_order_status(auth_client, order):
    res = auth_client.patch(
        f"/api/orders/{order.id}/status/",
        {"status": "completed"},
        format="json"
    )
    assert res.status_code == 403
@pytest.mark.django_db
def test_buy_out_of_stock_product(auth_client, out_of_stock_product):
    res = auth_client.post(
        "/api/cart/",
        {"product_id": out_of_stock_product.id, "quantity": 1},
        format="json"
    )
    assert res.status_code == 409
@pytest.mark.django_db
def test_create_order_unauthenticated(client):
    res = client.post("/api/orders/")
    assert res.status_code == 401
@pytest.mark.django_db
def test_get_order_unauthenticated(client, order):
    res = client.get(f"/api/orders/{order.id}/")
    assert res.status_code == 401
@pytest.mark.django_db
def test_update_order_unauthenticated(client, order):
    res = client.patch(
        f"/api/orders/{order.id}/",
        {"total": 200000},
        format="json"
    )
    assert res.status_code == 401
@pytest.mark.django_db
def test_delete_order_unauthenticated(client, order):
    res = client.delete(f"/api/orders/{order.id}/")
    assert res.status_code == 401
@pytest.mark.django_db
def test_list_orders_unauthenticated(client):
    res = client.get("/api/orders/")
    assert res.status_code == 401   
@pytest.mark.django_db
def test_checkout_requires_authentication():
    client = APIClient()
    response = client.post("/api/orders/1/checkout/")
    assert response.status_code == 401
@pytest.mark.django_db
def test_checkout_fails_and_rollbacks_when_stock_not_enough():
    client = APIClient()

    user = User.objects.create_user(username="user1", password="pass123")

    category = Category.objects.create(name="Phone")
    product1 = Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=1,
        category=category
    )
    product2 = Product.objects.create(
        name="iPhone 14",
        price=20000000,
        stock=10,
        category=category
    )

    login = client.post(
        "/api/auth/login/",
        {"username": "user1", "password": "pass123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # add to cart
    client.post("/api/cart/", {"product_id": product1.id, "quantity": 2}, format="json")
    client.post("/api/cart/", {"product_id": product2.id, "quantity": 1}, format="json")

    response = client.post("/api/orders/")

    assert response.status_code == 400
    

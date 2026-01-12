import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from api.models import Category, Product
from api.models import Order

@pytest.mark.django_db
def test_checkout_creates_order_and_clears_cart():
    client = APIClient()

    user = User.objects.create_user(username="khoa", password="anhkhoa123")

    category = Category.objects.create(name="Phone")
    product = Product.objects.create(
        name="iPhone 15", price=25000000, stock=10, category=category
    )

    login = client.post(
        "/api/auth/login/",
        {"username": "khoa", "password": "anhkhoa123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    client.post("/api/cart/", {"product_id": product.id, "quantity": 2}, format="json")

    response = client.post("/api/orders/")

    assert response.status_code == 201
    assert response.data["total"] == 50000000
    assert len(response.data["items"]) == 1

    cart = client.get("/api/cart/")
    assert cart.data["items"] == []

@pytest.mark.django_db
def test_user_cannot_view_other_users_order():
    client = APIClient()

    user1 = User.objects.create_user(username="user1", password="pass123")
    user2 = User.objects.create_user(username="user2", password="pass123")

    order = Order.objects.create(user=user1, total=100000)

    login = client.post(
        "/api/auth/login/",
        {"username": "user2", "password": "pass123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.get(f"/api/orders/{order.id}/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_update_order_status():
    client = APIClient()

    admin = User.objects.create_user(
        username="admin",
        password="admin123",
        is_staff=True
    )
    user = User.objects.create_user(username="user1", password="pass123")

    order = Order.objects.create(user=user, total=100000)

    login = client.post(
        "/api/auth/login/",
        {"username": "admin", "password": "admin123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.patch(
        f"/api/orders/{order.id}/status/",
        {"status": "paid"},
        format="json"
    )

    assert response.status_code == 200
    assert response.data["status"] == "paid"


@pytest.mark.django_db
def test_user_cannot_update_order_status():
    client = APIClient()

    user = User.objects.create_user(username="user1", password="pass123")
    order = Order.objects.create(user=user, total=100000)

    login = client.post(
        "/api/auth/login/",
        {"username": "user1", "password": "pass123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.patch(
        f"/api/orders/{order.id}/status/",
        {"status": "paid"},
        format="json"
    )

    assert response.status_code == 403


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

    # rollback check
    product1.refresh_from_db()
    product2.refresh_from_db()

    assert product1.stock == 1
    assert product2.stock == 10
    assert Order.objects.count() == 0

@pytest.mark.django_db
def test_user_can_list_their_orders():
    client = APIClient()

    user = User.objects.create_user(username="user1", password="pass123")

    order1 = Order.objects.create(user=user, total=100000)
    order2 = Order.objects.create(user=user, total=200000)

    login = client.post(
        "/api/auth/login/",
        {"username": "user1", "password": "pass123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.get("/api/orders/")

    assert response.status_code == 200
    assert len(response.data) == 2
    order_ids = [order["id"] for order in response.data]
    assert order1.id in order_ids
    assert order2.id in order_ids

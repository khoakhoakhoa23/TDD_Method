import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from api.models import Product, Category

@pytest.mark.django_db
def test_add_product_to_cart():
    client = APIClient()

    user = User.objects.create_user(
        username="khoa",
        password="anhkhoa123"
    )

    category = Category.objects.create(name="Phone")
    product = Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=10,
        category=category
    )

    # login
    login_response = client.post(
        "/api/auth/login/",
        {"username": "khoa", "password": "anhkhoa123"},
        format="json"
    )
    token = login_response.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.post(
        "/api/cart/",
        {"product_id": product.id, "quantity": 2},
        format="json"
    )

    assert response.status_code == 201
    assert response.data["product"]["id"] == product.id
    assert response.data["quantity"] == 2

@pytest.mark.django_db
def test_get_cart_returns_items():
    client = APIClient()

    user = User.objects.create_user(
        username="khoa",
        password="anhkhoa123"
    )

    category = Category.objects.create(name="Phone")
    product = Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=10,
        category=category
    )

    login = client.post(
        "/api/auth/login/",
        {"username": "khoa", "password": "anhkhoa123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    client.post(
        "/api/cart/",
        {"product_id": product.id, "quantity": 2},
        format="json"
    )

    response = client.get("/api/cart/")

    assert response.status_code == 200
    assert len(response.data["items"]) == 1
    assert response.data["items"][0]["quantity"] == 2
    assert response.data["total"] == 50000000

@pytest.mark.django_db
def test_update_cart_item_quantity():
    client = APIClient()

    user = User.objects.create_user(
        username="khoa",
        password="anhkhoa123"
    )

    category = Category.objects.create(name="Phone")
    product = Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=10,
        category=category
    )

    login = client.post(
        "/api/auth/login/",
        {"username": "khoa", "password": "anhkhoa123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    add = client.post(
        "/api/cart/",
        {"product_id": product.id, "quantity": 1},
        format="json"
    )
    item_id = add.data["id"]

    response = client.put(
        f"/api/cart/items/{item_id}/",
        {"quantity": 3},
        format="json"
    )

    assert response.status_code == 200
    assert response.data["quantity"] == 3

@pytest.mark.django_db
def test_add_product_to_cart_invalid_quantity():
    client = APIClient()

    user = User.objects.create_user(
        username="khoa",
        password="anhkhoa123"
    )

    category = Category.objects.create(name="Phone")
    product = Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=10,
        category=category
    )

    login = client.post(
        "/api/auth/login/",
        {"username": "khoa", "password": "anhkhoa123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.post(
        "/api/cart/",
        {"product_id": product.id, "quantity": 0},
        format="json"
    )

    assert response.status_code == 400

@pytest.mark.django_db
def test_update_cart_item_invalid_quantity():
    client = APIClient()

    user = User.objects.create_user(
        username="khoa",
        password="anhkhoa123"
    )

    category = Category.objects.create(name="Phone")
    product = Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=10,
        category=category
    )

    login = client.post(
        "/api/auth/login/",
        {"username": "khoa", "password": "anhkhoa123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    add = client.post(
        "/api/cart/",
        {"product_id": product.id, "quantity": 1},
        format="json"
    )
    item_id = add.data["id"]

    response = client.put(
        f"/api/cart/items/{item_id}/",
        {"quantity": 0},
        format="json"
    )

    assert response.status_code == 400

@pytest.mark.django_db
def test_update_cart_item_not_found():
    client = APIClient()

    user = User.objects.create_user(
        username="khoa",
        password="anhkhoa123"
    )

    login = client.post(
        "/api/auth/login/",
        {"username": "khoa", "password": "anhkhoa123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.put(
        "/api/cart/items/9999/",
        {"quantity": 1},
        format="json"
    )

    assert response.status_code == 404

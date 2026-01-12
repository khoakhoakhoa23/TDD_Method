import pytest
from rest_framework.test import APIClient
from api.models import Product, Category
from django.contrib.auth.models import User


@pytest.mark.django_db
def test_create_product():
    client = APIClient()

    data = {
        "name": "iPhone 15",
        "price": 25000000,
        "stock": 10
    }

    response = client.post("/api/products/", data, format="json")

    assert response.status_code == 201
    assert response.data["name"] == "iPhone 15"
    assert response.data["price"] == 25000000

@pytest.mark.django_db
def test_list_products():
    client = APIClient()

    Product.objects.create(name="iPhone 14", price=20000000, stock=5)
    Product.objects.create(name="iPhone 15", price=25000000, stock=10)

    response = client.get("/api/products/")

    assert response.status_code == 200
    assert len(response.data) == 2

@pytest.mark.django_db
def test_create_product_with_category():
    client = APIClient()

    category = Category.objects.create(name="Phone")

    data = {
        "name": "iPhone 15",
        "price": 25000000,
        "stock": 10,
        "category": category.id
    }

    response = client.post("/api/products/", data, format="json")

    assert response.status_code == 201
    assert response.data["name"] == "iPhone 15"
    assert response.data["category"] == category.id

@pytest.mark.django_db
def test_filter_products_by_category():
    client = APIClient()

    phone = Category.objects.create(name="Phone")
    laptop = Category.objects.create(name="Laptop")

    Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=10,
        category=phone
    )
    Product.objects.create(
        name="MacBook Pro",
        price=50000000,
        stock=5,
        category=laptop
    )

    response = client.get(f"/api/products/?category={phone.id}")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["name"] == "iPhone 15"


@pytest.mark.django_db
def test_product_returns_nested_category():
    client = APIClient()

    category = Category.objects.create(name="Phone")
    product = Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=10,
        category=category
    )

    response = client.get(f"/api/products/{product.id}/")

    assert response.status_code == 200
    assert response.data["category"]["id"] == category.id
    assert response.data["category"]["name"] == "Phone"


@pytest.mark.django_db
def test_normal_user_cannot_create_product():
    client = APIClient()

    user = User.objects.create_user(
        username="khoa",
        password="anhkhoa123"
    )

    category = Category.objects.create(name="Phone")

    login = client.post(
        "/api/auth/login/",
        {"username": "khoa", "password": "anhkhoa123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.post(
        "/api/products/",
        {
            "name": "iPhone 15",
            "price": 25000000,
            "stock": 10,
            "category_id": category.id
        },
        format="json"
    )

    assert response.status_code == 403

@pytest.mark.django_db
def test_admin_can_create_product():
    client = APIClient()

    admin = User.objects.create_user(
        username="admin",
        password="admin123",
        is_staff=True
    )

    category = Category.objects.create(name="Phone")

    login = client.post(
        "/api/auth/login/",
        {"username": "admin", "password": "admin123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.post(
        "/api/products/",
        {
            "name": "iPhone 15",
            "price": 25000000,
            "stock": 10,
            "category": category.id
        },
        format="json"
    )

    assert response.status_code == 201
    assert response.data["name"] == "iPhone 15"
@pytest.mark.django_db
def test_update_product():
    client = APIClient()

    product = Product.objects.create(
        name="iPhone 14",
        price=20000000,
        stock=5
    )

    data = {
        "name": "iPhone 14 Pro",
        "price": 23000000,
        "stock": 7
    }

    response = client.put(
        f"/api/products/{product.id}/",
        data,
        format="json"
    )

    assert response.status_code == 200
    assert response.data["name"] == "iPhone 14 Pro"
    assert response.data["price"] == 23000000
    assert response.data["stock"] == 7

@pytest.mark.django_db
def test_delete_product():
    client = APIClient()

    product = Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=10
    )

    response = client.delete(f"/api/products/{product.id}/")

    assert response.status_code == 204
    assert Product.objects.count() == 0
    
@pytest.mark.django_db
def test_retrieve_product():
    client = APIClient()

    product = Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=10
    )



    

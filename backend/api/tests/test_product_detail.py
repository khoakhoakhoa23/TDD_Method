import pytest
from rest_framework.test import APIClient
from api.models import Product, Category, CartItem, Cart
from django.contrib.auth import get_user_model
User = get_user_model()

@pytest.mark.django_db
def test_retrieve_product():
    client = APIClient()

    product = Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=10
    )

    response = client.get(f"/api/products/{product.id}/")

    assert response.status_code == 200
    assert response.data["name"] == "iPhone 15"
    assert response.data["price"] == 25000000
    assert response.data["stock"] == 10


@pytest.mark.django_db
def test_retrieve_product_not_found():
    client = APIClient()

    response = client.get("/api/products/9999/")

    assert response.status_code == 404

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
def test_list_cart_items():
    client = APIClient()

    user = User.objects.create_user(
        username="khoa",
        password="anhkhoa123"
    )

    category = Category.objects.create(name="Phone")

    product = Product.objects.create(
        name="iPhone 15",
        price=30000000,
        stock=10,
        category=category
    )

    cart = Cart.objects.create(user=user)

    CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=2
    )

    client.force_authenticate(user=user)

    response = client.get("/api/cart/")

    assert response.status_code == 200

    # Cart object
    assert "items" in response.data
    assert isinstance(response.data["items"], list)

    # Items
    assert len(response.data["items"]) == 1
    item = response.data["items"][0]

    assert item["product"]["name"] == "iPhone 15"
    assert item["quantity"] == 2

    # Total
    assert response.data["total"] == 60000000

@pytest.mark.django_db
def test_list_cart_items_unauthenticated():
    client = APIClient()

    response = client.get("/api/cart/")

    assert response.status_code == 401

@pytest.mark.django_db
def test_retrieve_product_with_category():
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
    assert response.data["name"] == "iPhone 15"
    assert response.data["category"]["name"] == "Phone"

@pytest.mark.django_db
def test_retrieve_product_no_category():
    client = APIClient()
    product = Product.objects.create(
        name="iPhone 15",
        price=25000000,
        stock=10
    )       
    response = client.get(f"/api/products/{product.id}/")
    assert response.status_code == 200
    assert response.data["name"] == "iPhone 15"
    assert response.data["category"] is None


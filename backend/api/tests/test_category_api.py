from xmlrpc import client
import pytest
from rest_framework.test import APIClient
from api.models import Category, Product
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_create_category():
    client = APIClient()

    data = {
        "name": "Phone"
    }

    response = client.post("/api/categories/", data, format="json")

    assert response.status_code == 201
    assert response.data["name"] == "Phone"


@pytest.mark.django_db
def test_list_categories():
    client = APIClient()

    Category.objects.create(name="Phone")
    Category.objects.create(name="Laptop")

    response = client.get("/api/categories/")

    assert response.status_code == 200
    assert len(response.data) == 2
@pytest.mark.django_db
def test_retrieve_category():
    client = APIClient()

    category = Category.objects.create(name="Phone")

    response = client.get(f"/api/categories/{category.id}/")

    assert response.status_code == 200
    assert response.data["name"] == "Phone"
@pytest.mark.django_db
def test_update_category():
    client = APIClient()

    category = Category.objects.create(name="Phone")

    data = {
        "name": "Smartphone"
    }

    response = client.put(
        f"/api/categories/{category.id}/",
        data,
        format="json"
    )

    assert response.status_code == 200
    assert response.data["name"] == "Smartphone"
@pytest.mark.django_db
def test_delete_category():
    client = APIClient()

    category = Category.objects.create(name="Phone")

    response = client.delete(f"/api/categories/{category.id}/")

    assert response.status_code == 204

    # Verify deletion
    response = client.get(f"/api/categories/{category.id}/")
    assert response.status_code == 404
    
@pytest.mark.django_db

def test_normal_user_cannot_create_category():
    client = APIClient()

    user = User.objects.create_user(
        username="user1",
        password="password123"
    )

    login = client.post(
        "/api/auth/login/",
        {"username": "user1", "password": "password123"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.post(
        "/api/categories/",
        {"name": "Laptop"},
        format="json"
    )

    assert response.status_code == 403

@pytest.mark.django_db
def test_admin_can_create_category():
    client = APIClient()

    admin_user = User.objects.create_superuser(
        username="admin",
        password="adminpass"
    )

    login = client.post(
        "/api/auth/login/",
        {"username": "admin", "password": "adminpass"},
        format="json"
    )
    token = login.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.post(
        "/api/categories/",
        {"name": "Laptop"},
        format="json"
    )

    assert response.status_code == 201
    assert response.data["name"] == "Laptop"
@pytest.mark.django_db
def test_create_category_with_empty_name_should_fail():
    client = APIClient()

    data = {
        "name": ""
    }

    response = client.post("/api/categories/", data, format="json")

    assert response.status_code == 400
    assert "name" in str(response.data).lower() or "name" in response.data
@pytest.mark.django_db
def test_create_category_with_duplicate_name_should_fail():
    client = APIClient()

    Category.objects.create(name="Phone")

    data = {
        "name": "Phone"
    }

    response = client.post("/api/categories/", data, format="json")

    assert response.status_code == 400
    assert "name" in str(response.data).lower() or "name" in response.data
@pytest.mark.django_db
def test_update_category_with_empty_name_should_fail(): 
    client = APIClient()

    category = Category.objects.create(name="Phone")

    data = {
        "name": ""
    }

    response = client.put(
        f"/api/categories/{category.id}/",
        data,
        format="json"
    )

    assert response.status_code == 400
    assert "name" in str(response.data).lower() or "name" in response.data
@pytest.mark.django_db
def test_update_category_with_duplicate_name_should_fail():
    client = APIClient()

    Category.objects.create(name="Phone")
    category2 = Category.objects.create(name="Laptop")

    data = {
        "name": "Phone"
    }

    response = client.put(
        f"/api/categories/{category2.id}/",
        data,
        format="json"
    )

    assert response.status_code == 400
    assert "name" in str(response.data).lower() or "name" in response.data
@pytest.mark.django_db
def test_list_categories_empty():
    client = APIClient()

    response = client.get("/api/categories/")

    assert response.status_code == 200
    assert len(response.data) == 0
    
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
def test_update_product_detail():
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
def test_create_order_from_cart():
    client = APIClient()

    user = User.objects.create_user(username="khoa", password="anhkhoa123")
    category = Category.objects.create(name="Phone")
    product = Product.objects.create(
        name="iPhone 15", price=25000000, stock=10, category=category
    )
    login = client.post(
        "/api/auth/login/",
        {"username": "khoa", "password" : "anhkhoa123"},
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

    # ✅ authenticate trực tiếp
    client.force_authenticate(user=user)

    # add to cart
    add_response = client.post(
        "/api/cart/",
        {"product_id": product.id, "quantity": 2},
        format="json"
    )

    cart_item_id = add_response.data["id"]

    # update quantity
    response = client.put(
    f"/api/cart/items/{cart_item_id}/",
    {"quantity": 5},
    format="json"
    )

    assert response.status_code == 200
    assert response.data["quantity"] == 5
    cart_response = client.get("/api/cart/")
    assert cart_response.data["total"] == 125000000




@pytest.mark.django_db
def update_cart_item_quantity(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    cart_item_id = request.data.get("cart_item_id")
    quantity = request.data.get("quantity")

    cart_item = get_object_or_404(
        CartItem,
        id=cart_item_id,
        cart__user=request.user
    )

    cart_item.quantity = quantity
    cart_item.save()

    return JsonResponse({
        "id": cart_item.id,
        "quantity": cart_item.quantity,
        "total_price": cart_item.quantity * cart_item.product.price
    })

"""
Shared fixtures for all tests.
This file is automatically discovered by pytest.
"""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from api.models import Category, Product, Cart, CartItem


@pytest.fixture
def api_client():
    """Basic API client without authentication"""
    return APIClient()


@pytest.fixture
def user():
    """Create a test user"""
    return User.objects.create_user(
        username="testuser",
        password="testpass123"
    )


@pytest.fixture
def admin_user():
    """Create a test admin user"""
    return User.objects.create_user(
        username="admin",
        password="admin123",
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def authenticated_client(user):
    """API client authenticated as regular user"""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(admin_user):
    """API client authenticated as admin"""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def category():
    """Create a test category"""
    return Category.objects.create(name="Test Category")


@pytest.fixture
def product(category):
    """Create a test product"""
    return Product.objects.create(
        name="Test Product",
        price=100000,
        stock=10,
        category=category
    )


@pytest.fixture
def product_without_category():
    """Create a test product without category"""
    return Product.objects.create(
        name="Test Product No Category",
        price=50000,
        stock=5
    )


@pytest.fixture
def cart(user):
    """Create a test cart for user"""
    return Cart.objects.create(user=user)


@pytest.fixture
def cart_with_item(cart, product):
    """Create a cart with one item"""
    CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=2
    )
    return cart


@pytest.fixture
def multiple_products(category):
    """Create multiple test products"""
    products = []
    for i in range(5):
        products.append(Product.objects.create(
            name=f"Product {i+1}",
            price=(i+1) * 10000,
            stock=10,
            category=category
        ))
    return products


@pytest.fixture
def multiple_categories():
    """Create multiple test categories"""
    categories = []
    for name in ["Electronics", "Clothing", "Books", "Food"]:
        categories.append(Category.objects.create(name=name))
    return categories


@pytest.fixture
def authenticated_api_client(user):
    """API client authenticated as regular user"""
    client = APIClient()
    client.force_authenticate(user=user)
    return client
 
@pytest.fixture
def admin_api_client(admin_user):
    """API client authenticated as admin"""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client
@pytest.fixture
def product_with_category(category):
    """Create a test product with category"""
    return Product.objects.create(
        name="Test Product With Category",
        price=150000,
        stock=20,
        category=category
    )





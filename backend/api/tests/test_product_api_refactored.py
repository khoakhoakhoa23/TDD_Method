"""
Refactored Product API Tests using TDD fixtures
This demonstrates how to use fixtures to reduce boilerplate
"""
import pytest
from rest_framework.test import APIClient
from api.models import Product, Category


class TestProductAPI:
    """Test suite for Product CRUD operations using fixtures"""

    @pytest.mark.django_db
    def test_create_product(self, admin_client):
        """Test creating a product"""
        data = {
            "name": "iPhone 15",
            "price": 25000000,
            "stock": 10
        }

        response = admin_client.post("/api/products/", data, format="json")

        assert response.status_code == 201
        assert response.data["name"] == "iPhone 15"
        assert response.data["price"] == 25000000

    @pytest.mark.django_db
    def test_list_products(self, api_client, multiple_products):
        """Test listing all products"""
        response = api_client.get("/api/products/")

        assert response.status_code == 200
        assert len(response.data) == 5  # 5 products from fixture

    @pytest.mark.django_db
    def test_create_product_with_category(self, admin_client, category):
        """Test creating a product with category"""
        data = {
            "name": "iPhone 15",
            "price": 25000000,
            "stock": 10,
            "category": category.id
        }

        response = admin_client.post("/api/products/", data, format="json")

        assert response.status_code == 201
        assert response.data["name"] == "iPhone 15"
        assert response.data["category"] == category.id

    @pytest.mark.django_db
    def test_filter_products_by_category(self, api_client, multiple_categories):
        """Test filtering products by category"""
        phone_category = multiple_categories[0]
        laptop_category = multiple_categories[1]

        Product.objects.create(
            name="iPhone 15",
            price=25000000,
            stock=10,
            category=phone_category
        )
        Product.objects.create(
            name="MacBook Pro",
            price=50000000,
            stock=5,
            category=laptop_category
        )

        response = api_client.get(f"/api/products/?category={phone_category.id}")

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["name"] == "iPhone 15"

    @pytest.mark.django_db
    def test_product_detail_returns_nested_category(self, api_client, product):
        """Test product detail returns nested category information"""
        response = api_client.get(f"/api/products/{product.id}/")

        assert response.status_code == 200
        assert response.data["category"]["id"] == product.category.id
        assert response.data["category"]["name"] == product.category.name

    @pytest.mark.django_db
    def test_normal_user_cannot_create_product(self, authenticated_client, category):
        """Test that normal user cannot create product"""
        data = {
            "name": "iPhone 15",
            "price": 25000000,
            "stock": 10,
            "category": category.id
        }

        response = authenticated_client.post("/api/products/", data, format="json")

        assert response.status_code == 403

    @pytest.mark.django_db
    def test_admin_can_create_product(self, admin_client, category):
        """Test that admin can create product"""
        data = {
            "name": "iPhone 15",
            "price": 25000000,
            "stock": 10,
            "category": category.id
        }

        response = admin_client.post("/api/products/", data, format="json")

        assert response.status_code == 201
        assert response.data["name"] == "iPhone 15"

    @pytest.mark.django_db
    def test_update_product(self, admin_client, product):
        """Test updating a product"""
        data = {
            "name": "Updated Product Name",
            "price": product.price,
            "stock": product.stock,
            "category": product.category.id if product.category else None
        }

        response = admin_client.put(f"/api/products/{product.id}/", data, format="json")

        assert response.status_code == 200
        assert response.data["name"] == "Updated Product Name"

    @pytest.mark.django_db
    def test_delete_product(self, admin_client, product):
        """Test deleting a product"""
        product_id = product.id

        response = admin_client.delete(f"/api/products/{product_id}/")

        assert response.status_code == 204

        # Verify deletion
        get_response = admin_client.get(f"/api/products/{product_id}/")
        assert get_response.status_code == 404









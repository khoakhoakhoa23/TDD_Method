"""
TDD Tests for Product Validation
Following RED-GREEN-REFACTOR pattern
"""
import pytest
from rest_framework.test import APIClient
from api.models import Product, Category


class TestProductValidation:
    """
    Test suite for product validation rules.
    These tests are written BEFORE implementing validation logic (TDD).
    """

    @pytest.mark.django_db
    def test_create_product_with_negative_price_should_fail(self, admin_client):
        """
        RED: Test that creating a product with negative price should fail.
        This test will fail initially because validation doesn't exist yet.
        """
        data = {
            "name": "Test Product",
            "price": -1000,  # Invalid: negative price
            "stock": 10
        }

        response = admin_client.post("/api/products/", data, format="json")

        # Assert: Should return 400 Bad Request
        assert response.status_code == 400
        assert "price" in str(response.data).lower() or "price" in response.data

    @pytest.mark.django_db
    def test_create_product_with_zero_price_should_succeed(self, admin_client):
        """
        Test that zero price is allowed (free product).
        """
        data = {
            "name": "Free Product",
            "price": 0,
            "stock": 10
        }

        response = admin_client.post("/api/products/", data, format="json")

        assert response.status_code == 201
        assert response.data["price"] == 0

    @pytest.mark.django_db
    def test_create_product_with_negative_stock_should_fail(self, admin_client):
        """
        RED: Test that creating a product with negative stock should fail.
        """
        data = {
            "name": "Test Product",
            "price": 1000,
            "stock": -5  # Invalid: negative stock
        }

        response = admin_client.post("/api/products/", data, format="json")

        assert response.status_code == 400
        assert "stock" in str(response.data).lower() or "stock" in response.data

    @pytest.mark.django_db
    def test_create_product_without_name_should_fail(self, admin_client):
        """
        RED: Test that creating a product without name should fail.
        """
        data = {
            "price": 1000,
            "stock": 10
            # Missing: name
        }

        response = admin_client.post("/api/products/", data, format="json")

        assert response.status_code == 400
        assert "name" in str(response.data).lower() or "name" in response.data

    @pytest.mark.django_db
    def test_create_product_with_empty_name_should_fail(self, admin_client):
        """
        RED: Test that creating a product with empty name should fail.
        """
        data = {
            "name": "",  # Invalid: empty name
            "price": 1000,
            "stock": 10
        }

        response = admin_client.post("/api/products/", data, format="json")

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_create_product_with_very_long_name_should_fail(self, admin_client):
        """
        RED: Test that creating a product with name exceeding max length should fail.
        """
        data = {
            "name": "A" * 300,  # Invalid: too long (max 255)
            "price": 1000,
            "stock": 10
        }

        response = admin_client.post("/api/products/", data, format="json")

        assert response.status_code == 400

    @pytest.mark.django_db
    def test_update_product_price_to_negative_should_fail(self, admin_client, product):
        """
        RED: Test that updating product price to negative should fail.
        """
        data = {
            "name": product.name,
            "price": -500,  # Invalid: negative price
            "stock": product.stock,
            "category": product.category.id if product.category else None
        }
        
        response = admin_client.put(f"/api/products/{product.id}/", data, format="json")

        assert response.status_code == 400
        assert "price" in str(response.data).lower() or "price" in response.data

    @pytest.mark.django_db
    def test_create_product_with_valid_data_should_succeed(self, admin_client, category):
        """
        GREEN: Test that creating a product with valid data should succeed.
        """
        data = {
            "name": "Valid Product",
            "price": 100000,
            "stock": 10,
            "category": category.id
        }

        response = admin_client.post("/api/products/", data, format="json")

        assert response.status_code == 201
        assert response.data["name"] == "Valid Product"
        assert response.data["price"] == 100000
        assert response.data["stock"] == 10

    @pytest.mark.django_db
    def test_create_product_with_max_length_name_should_succeed(self, admin_client):
        """
        GREEN: Test that creating a product with name at max length should succeed.
        """
        data = {
            "name": "B" * 255,  # Valid: max length
            "price": 5000,
            "stock": 15
        }

        response = admin_client.post("/api/products/", data, format="json")

        assert response.status_code == 201
        assert response.data["name"] == "B" * 255   
        assert response.data["price"] == 5000
        assert response.data["stock"] == 15
    @pytest.mark.django_db
    def test_create_product_with_large_stock_should_succeed(self, admin_client):
        """
        GREEN: Test that creating a product with a large stock value should succeed.
        """
        data = {
            "name": "Bulk Product",
            "price": 2000,
            "stock": 1000000  # Large stock value
        }

        response = admin_client.post("/api/products/", data, format="json")

        assert response.status_code == 201
        assert response.data["name"] == "Bulk Product"
        assert response.data["price"] == 2000
        assert response.data["stock"] == 1000000
    @pytest.mark.django_db
    def test_update_product_stock_to_zero_should_succeed(self, admin_client, product):
        """
        GREEN: Test that updating product stock to zero should succeed.
        """
        data = {
            "name": product.name,
            "price": product.price,
            "stock": 0,  # Valid: zero stock
            "category": product.category.id if product.category else None
        }
        response = admin_client.put(f"/api/products/{product.id}/", data, format="json")
        assert response.status_code == 200
        assert response.data["stock"] == 0

 





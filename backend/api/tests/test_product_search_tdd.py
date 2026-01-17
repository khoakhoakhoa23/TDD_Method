
import pytest
from rest_framework.test import APIClient
from api.models import Product, Category


class TestProductSearch:
    """
    Test suite for product search functionality.
    These tests are written BEFORE implementing search logic (TDD).
    """

    @pytest.fixture
    def setup_products(self, category):
        """Setup test products for search tests"""
        products = [
            Product.objects.create(
                name="iPhone 15 Pro Max",
                price=30000000,
                stock=10,
                category=category
            ),
            Product.objects.create(
                name="Samsung Galaxy S24",
                price=25000000,
                stock=5,
                category=category
            ),
            Product.objects.create(
                name="iPhone 14",
                price=20000000,
                stock=8,
                category=category
            ),
            Product.objects.create(
                name="Xiaomi Redmi Note 13",
                price=5000000,
                stock=20,
                category=category
            ),
        ]
        return products

    @pytest.mark.django_db
    def test_search_products_by_name_should_return_matching_results(self, api_client, setup_products):
        """
        RED: Test searching products by name.
        This test will fail initially because search doesn't exist yet.
        """
        response = api_client.get("/api/products/?search=iPhone")

        assert response.status_code == 200
        assert len(response.data) == 2  # Should find iPhone 15 and iPhone 14
        assert all("iPhone" in product["name"] for product in response.data)

    @pytest.mark.django_db
    def test_search_products_case_insensitive(self, api_client, setup_products):
        """
        RED: Test that search is case-insensitive.
        """
        response = api_client.get("/api/products/?search=iphone")

        assert response.status_code == 200
        assert len(response.data) == 2

    @pytest.mark.django_db
    def test_search_products_with_no_results(self, api_client, setup_products):
        """
        RED: Test searching with no matching results.
        """
        response = api_client.get("/api/products/?search=NonExistentProduct")

        assert response.status_code == 200
        assert len(response.data) == 0

    @pytest.mark.django_db
    def test_search_products_with_empty_query_returns_all(self, api_client, setup_products):
        """
        RED: Test that empty search query returns all products.
        """
        response = api_client.get("/api/products/?search=")

        assert response.status_code == 200
        assert len(response.data) == 4  # All products

    @pytest.mark.django_db
    def test_search_products_partial_match(self, api_client, setup_products):
        """
        RED: Test that search works with partial matches.
        """
        response = api_client.get("/api/products/?search=Galaxy")

        assert response.status_code == 200
        assert len(response.data) == 1
        assert "Galaxy" in response.data[0]["name"]

    @pytest.mark.django_db
    def test_search_products_combined_with_category_filter(self, api_client, setup_products, category):
        """
        RED: Test that search works combined with category filter.
        """
        response = api_client.get(f"/api/products/?category={category.id}&search=iPhone")

        assert response.status_code == 200
        assert len(response.data) == 2
        assert all("iPhone" in product["name"] for product in response.data)


    @pytest.mark.django_db
    def test_search_products_pagination(self, api_client, setup_products):
        """
        RED: Test that search results are paginated.
        """
        response = api_client.get("/api/products/?search=iPhone&page=1&page_size=1")

        assert response.status_code == 200
        assert len(response.data) == 1  # Only 1 result per page
        assert "iPhone" in response.data[0]["name"]
        # Fetch second page
        response_page_2 = api_client.get("/api/products/?search=iPhone&page=2&page_size=1") 
        assert response_page_2.status_code == 200
        assert len(response_page_2.data) == 1
        assert "iPhone" in response_page_2.data[0]["name"]
        assert response.data[0]["id"] != response_page_2.data[0]["id"]  # Different products on different pages
    @pytest.mark.django_db
    def test_search_products_special_characters(self, api_client, setup_products):
        """
        RED: Test that search handles special characters.
        """
        # Add a product with special characters
        special_product = Product.objects.create(
            name="Nokia-3310!",
            price=2000000,
            stock=15,
            category=setup_products[0].category
        )

        response = api_client.get("/api/products/?search=Nokia-3310!")

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Nokia-3310!"
    @pytest.mark.django_db
    def test_search_products_numeric_query(self, api_client, setup_products):
        """
        RED: Test that search works with numeric queries.
        """
        response = api_client.get("/api/products/?search=14")

        assert response.status_code == 200
        assert len(response.data) == 1
        assert "14" in response.data[0]["name"]
    @pytest.mark.django_db
    def test_search_products_multiple_keywords(self, api_client, setup_products):
        """
        RED: Test that search works with multiple keywords.
        """
        response = api_client.get("/api/products/?search=iPhone+Pro")

        assert response.status_code == 200
        assert len(response.data) == 1
        assert "iPhone 15 Pro Max" == response.data[0]["name"]
    @pytest.mark.django_db
    def test_search_products_whitespace_query(self, api_client, setup_products):
        """
        RED: Test that search handles leading/trailing whitespace.
        """
        response = api_client.get("/api/products/?search=  iPhone  ")

        assert response.status_code == 200
        assert len(response.data) == 2
        assert all("iPhone" in product["name"] for product in response.data)
    @pytest.mark.django_db
    def test_search_products_special_language_characters(self, api_client, category):
        """
        RED: Test that search handles special language characters.
        """
        # Add a product with special language characters
        special_product = Product.objects.create(
            name="Café Mocha",
            price=150000,
            stock=10,
            category=category
        )

        response = api_client.get("/api/products/?search=Café")

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Café Mocha"
    @pytest.mark.django_db
    def test_search_products_long_query(self, api_client, setup_products):
        """
        RED: Test that search handles long query strings.
        """
        long_query = "iPhone " * 50  # Very long query string

        response = api_client.get(f"/api/products/?search={long_query.strip()}")

        assert response.status_code == 200
        assert len(response.data) == 2
        assert all("iPhone" in product["name"] for product in response.data)    

    



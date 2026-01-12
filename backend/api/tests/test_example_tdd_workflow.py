
import pytest
from rest_framework.test import APIClient
from api.models import Product


class TestTDDWorkflowExample:
   

    @pytest.mark.django_db
    def test_get_product_statistics_endpoint(self, api_client, multiple_products):
       
        response = api_client.get("/api/products/statistics/")

        
        assert response.status_code == 200
        assert "total_products" in response.data
        assert "total_value" in response.data
        assert "average_price" in response.data
        assert response.data["total_products"] == 5  # From multiple_products fixture

    @pytest.mark.django_db
    def test_product_statistics_calculates_correctly(self, api_client):
       
        # Create products with known values
        Product.objects.create(name="Product 1", price=10000, stock=5)
        Product.objects.create(name="Product 2", price=20000, stock=3)
        Product.objects.create(name="Product 3", price=30000, stock=2)

        response = api_client.get("/api/products/statistics/")

        assert response.status_code == 200
        assert response.data["total_products"] == 3
        assert response.data["total_value"] == 60000  # 10000 + 20000 + 30000
        assert response.data["average_price"] == 20000  # 60000 / 3

    @pytest.mark.django_db
    def test_product_statistics_with_no_products(self, api_client):
    
        response = api_client.get("/api/products/statistics/")

        assert response.status_code == 200
        assert response.data["total_products"] == 0
        assert response.data["total_value"] == 0
        assert response.data["average_price"] == 0


    @pytest.mark.django_db
    def test_product_statistics_with_large_numbers(self, api_client):   
        # Create products with large price values
        Product.objects.create(name="Expensive Product 1", price=10**9, stock=1)
        Product.objects.create(name="Expensive Product 2", price=2 * 10**9, stock=1)

        response = api_client.get("/api/products/statistics/")

        assert response.status_code == 200
        assert response.data["total_products"] == 2
        assert response.data["total_value"] == 3 * 10**9  # 10^9 + 2*10^9
        assert response.data["average_price"] == 1.5 * 10**9  # (3*10^9) / 2
    
    @pytest.mark.django_db
    def test_product_statistics_with_negative_prices(self, api_client):
        # Create products with negative price values
        Product.objects.create(name="Defective Product 1", price=-1000, stock=1)
        Product.objects.create(name="Defective Product 2", price=-2000, stock=1)

        response = api_client.get("/api/products/statistics/")

        assert response.status_code == 200
        assert response.data["total_products"] == 2
        assert response.data["total_value"] == -3000  # -1000 + -2000
        assert response.data["average_price"] == -1500  # (-3000) / 2
   





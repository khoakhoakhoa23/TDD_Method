
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


"""
STEP 2 (GREEN): After writing tests, implement the endpoint

# In views.py:
@api_view(['GET'])
def product_statistics(request):
    products = Product.objects.all()
    total_products = products.count()
    total_value = sum(p.price for p in products)
    average_price = total_value / total_products if total_products > 0 else 0
    
    return Response({
        "total_products": total_products,
        "total_value": total_value,
        "average_price": average_price
    }, status=200)

# In urls.py:
path('products/statistics/', views.product_statistics, name='product-statistics'),

STEP 3 (REFACTOR): Improve the code

# Use aggregation for better performance:
from django.db.models import Count, Sum, Avg

@api_view(['GET'])
def product_statistics(request):
    stats = Product.objects.aggregate(
        total_products=Count('id'),
        total_value=Sum('price'),
        average_price=Avg('price')
    )
    
    return Response({
        "total_products": stats['total_products'] or 0,
        "total_value": stats['total_value'] or 0,
        "average_price": stats['average_price'] or 0
    }, status=200)

All tests should still pass after refactoring!
"""





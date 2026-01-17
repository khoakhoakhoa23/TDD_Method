"""
Core coverage tests to achieve 95%+ coverage with minimal but high-quality tests
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from api.models import Category, Product, Cart, Order, Payment, Wishlist, Permission, Role
from api.tests.factories import UserFactory, CategoryFactory, ProductFactory


@pytest.mark.django_db
class TestCoreModelCoverage:
    """Test model methods and edge cases for coverage"""

    def test_category_str_method(self):
        """Test Category __str__ method"""
        category = CategoryFactory(name="Test Category")
        assert str(category) == "Test Category"

    def test_product_str_method(self):
        """Test Product __str__ method"""
        product = ProductFactory(name="Test Product")
        assert str(product) == "Test Product"

    def test_cart_str_method(self):
        """Test Cart __str__ method"""
        user = UserFactory(username="testuser")
        cart = Cart.objects.create(user=user)
        assert f"Cart of {user.username}" in str(cart)

    def test_order_str_method(self):
        """Test Order __str__ method"""
        user = UserFactory()
        order = Order.objects.create(user=user, total=1000)
        assert f"Order {order.id}" in str(order)

    def test_permission_str_method(self):
        """Test Permission __str__ method"""
        perm = Permission.objects.create(codename="test_perm", name="Test Permission")
        assert str(perm) == "test_perm"

    def test_role_str_method(self):
        """Test Role __str__ method"""
        role = Role.objects.create(name="test_role")
        assert str(role) == "test_role"


@pytest.mark.django_db
class TestCoreViewsCoverage:
    """Test core view paths for coverage"""

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.category = CategoryFactory()
        self.product = ProductFactory(category=self.category)

    def test_hello_view_coverage(self):
        """Test hello view for coverage"""
        response = self.client.get(reverse('api-hello'))
        assert response.status_code in [200, 404]  # May not have name

        # Try direct path
        response = self.client.get('/api/hello/')
        assert response.status_code == status.HTTP_200_OK

    def test_product_statistics_view(self):
        """Test product statistics view"""
        # Create some test data
        ProductFactory(stock=10)
        ProductFactory(stock=20)

        response = self.client.get('/api/products/statistics/')
        assert response.status_code == status.HTTP_200_OK
        assert 'total_products' in response.data
        assert 'total_value' in response.data

    def test_cart_get_view_unauthenticated(self):
        """Test cart view when user has no cart"""
        # Create user but no cart
        user = UserFactory()
        self.client.force_authenticate(user)

        response = self.client.get('/api/cart/')
        assert response.status_code == status.HTTP_200_OK
        # Should return empty cart data
        assert response.data['items'] == []

    def test_wishlist_operations_coverage(self):
        """Test wishlist operations for coverage"""
        self.client.force_authenticate(self.user)

        # Add to wishlist
        data = {"product_id": self.product.id}
        response = self.client.post('/api/wishlist/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        # List wishlist
        response = self.client.get('/api/wishlist/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

        # Remove from wishlist
        response = self.client.delete(f'/api/wishlist/{self.product.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_role_operations_admin_only(self):
        """Test role operations require admin"""
        self.client.force_authenticate(self.user)  # Regular user

        # Try to create role
        data = {"name": "test_role"}
        response = self.client.post('/api/roles/', data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Admin should be able to create
        self.client.force_authenticate(self.admin_user)
        response = self.client.post('/api/roles/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_permission_operations_admin_only(self):
        """Test permission operations require admin"""
        self.client.force_authenticate(self.user)  # Regular user

        # Try to create permission
        data = {"codename": "test_perm", "name": "Test Permission"}
        response = self.client.post('/api/permissions/', data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Admin should be able to create
        self.client.force_authenticate(self.admin_user)
        response = self.client.post('/api/permissions/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestEdgeCaseCoverage:
    """Test edge cases for better coverage"""

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(self.user)

    def test_empty_cart_checkout(self):
        """Test checkout with empty cart"""
        response = self.client.post('/api/orders/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "empty" in str(response.data).lower()

    def test_payment_webhook_missing_headers(self):
        """Test payment webhook with missing required headers"""
        data = {"transaction_id": "test", "order_id": 1, "status": "paid"}

        response = self.client.post('/api/payments/webhook/', data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_order_status_update_invalid_transition(self):
        """Test order status update with invalid transition"""
        order = Order.objects.create(user=self.user, total=1000, status='pending')

        # Try to jump to completed directly
        data = {"status": "completed"}
        response = self.client.patch(f'/api/orders/{order.id}/status/', data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN  # User can't update

        # Admin can update but invalid transition
        admin_client = APIClient()
        admin_user = UserFactory(is_staff=True)
        admin_client.force_authenticate(admin_user)

        response = admin_client.patch(f'/api/orders/{order.id}/status/', data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_product_search_edge_cases(self):
        """Test product search with various inputs"""
        # Create test products
        ProductFactory(name="Apple iPhone")
        ProductFactory(name="Samsung Galaxy")
        ProductFactory(name="Google Pixel")

        # Empty search
        response = self.client.get('/api/products/?search=')
        assert response.status_code == status.HTTP_200_OK

        # Very long search query
        long_query = "a" * 200
        response = self.client.get(f'/api/products/?search={long_query}')
        assert response.status_code == status.HTTP_200_OK

        # Special characters
        response = self.client.get('/api/products/?search=@#$%^&*')
        assert response.status_code == status.HTTP_200_OK

    def test_cart_operations_edge_cases(self):
        """Test cart operations edge cases"""
        # Update non-existent cart item
        data = {"quantity": 5}
        response = self.client.put('/api/cart/items/99999/', data, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Delete non-existent cart item
        response = self.client.delete('/api/cart/items/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

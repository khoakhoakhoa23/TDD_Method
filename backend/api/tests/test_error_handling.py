import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from api.models import Category, Product, Order, Payment
from api.tests.factories import UserFactory, CategoryFactory, ProductFactory


@pytest.mark.django_db
class TestProductAPIErrorHandling:
    """Test error handling paths for Product APIs"""

    def setup_method(self):
        self.client = APIClient()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.regular_user = UserFactory()
        self.category = CategoryFactory()

    def test_create_product_with_invalid_category_id(self):
        """Test creating product with non-existent category ID"""
        self.client.force_authenticate(self.admin_user)

        data = {
            "name": "Test Product",
            "price": 1000,
            "stock": 10,
            "category": 99999  # Non-existent category
        }

        response = self.client.post(reverse('product-list-create'), data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "object does not exist" in str(response.data).lower()

    def test_update_product_with_invalid_category_id(self):
        """Test updating product with non-existent category ID"""
        product = ProductFactory(category=self.category)
        self.client.force_authenticate(self.admin_user)

        data = {
            "name": "Updated Product",
            "price": 2000,
            "stock": 20,
            "category": 99999  # Non-existent category
        }

        response = self.client.put(
            reverse('product-detail', kwargs={'pk': product.id}),
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "object does not exist" in str(response.data).lower()

    def test_product_detail_not_found(self):
        """Test accessing non-existent product detail"""
        self.client.force_authenticate(self.regular_user)

        response = self.client.get(reverse('product-detail', kwargs={'pk': 99999}))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['error'] == "Product not found"

    def test_update_product_not_found(self):
        """Test updating non-existent product"""
        self.client.force_authenticate(self.admin_user)

        data = {"name": "Updated Name", "price": 1000, "stock": 10}

        response = self.client.put(
            reverse('product-detail', kwargs={'pk': 99999}),
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['error'] == "Product not found"

    def test_delete_product_not_found(self):
        """Test deleting non-existent product"""
        self.client.force_authenticate(self.admin_user)

        response = self.client.delete(reverse('product-detail', kwargs={'pk': 99999}))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['error'] == "Product not found"


@pytest.mark.django_db
class TestCategoryAPIErrorHandling:
    """Test error handling paths for Category APIs"""

    def setup_method(self):
        self.client = APIClient()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.regular_user = UserFactory()
        self.category = CategoryFactory()

    def test_category_detail_not_found(self):
        """Test accessing non-existent category detail"""
        self.client.force_authenticate(self.regular_user)

        response = self.client.get(reverse('category-detail', kwargs={'pk': 99999}))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_category_not_found(self):
        """Test updating non-existent category"""
        self.client.force_authenticate(self.admin_user)

        data = {"name": "Updated Category"}

        response = self.client.put(
            reverse('category-detail', kwargs={'pk': 99999}),
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_category_not_found(self):
        """Test deleting non-existent category"""
        self.client.force_authenticate(self.admin_user)

        response = self.client.delete(reverse('category-detail', kwargs={'pk': 99999}))
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestOrderAPIErrorHandling:
    """Test error handling paths for Order APIs"""

    def setup_method(self):
        self.client = APIClient()
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.product = ProductFactory(stock=10)

    def test_order_detail_not_found(self):
        """Test accessing non-existent order"""
        self.client.force_authenticate(self.user1)

        response = self.client.get(reverse('order-detail', kwargs={'pk': 99999}))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_order_detail_unauthorized(self):
        """Test accessing another user's order"""
        # Create order for user1
        order = Order.objects.create(user=self.user1, total=1000)

        # Try to access as user2
        self.client.force_authenticate(self.user2)

        response = self.client.get(reverse('order-detail', kwargs={'pk': order.id}))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_checkout_order_redirect(self):
        """Test checkout endpoint redirects to main orders endpoint"""
        self.client.force_authenticate(self.user1)

        response = self.client.post(reverse('checkout', kwargs={'pk': 99999}))
        assert response.status_code == status.HTTP_200_OK
        assert "Use POST /api/orders/" in str(response.data)

    def test_update_order_status_invalid_transition(self):
        """Test invalid order status transitions"""
        order = Order.objects.create(user=self.user1, total=1000, status='pending')
        self.client.force_authenticate(self.admin_user)

        # Try to jump from pending directly to completed (invalid)
        data = {"status": "completed"}

        response = self.client.patch(
            reverse('update-order-status', kwargs={'pk': order.id}),
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid status transition" in str(response.data).lower()


@pytest.mark.django_db
class TestPaymentAPIErrorHandling:
    """Test error handling paths for Payment APIs"""

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.order = Order.objects.create(user=self.user, total=1000)

    def test_payment_status_not_found(self):
        """Test getting status of non-existent payment"""
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse('payment-status', kwargs={'pk': 99999}))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_payment_status_unauthorized(self):
        """Test accessing another user's payment status"""
        user2 = UserFactory()
        order2 = Order.objects.create(user=user2, total=1000)
        payment = Payment.objects.create(
            order=order2,
            provider='vnpay',
            amount=1000,
            status='pending'
        )

        self.client.force_authenticate(self.user)

        response = self.client.get(reverse('payment-status', kwargs={'pk': payment.id}))
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCartAPIErrorHandling:
    """Test error handling paths for Cart APIs"""

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.product = ProductFactory(stock=10)

    def test_cart_item_detail_not_found(self):
        """Test updating non-existent cart item"""
        self.client.force_authenticate(self.user)

        data = {"quantity": 5}

        response = self.client.put(
            reverse('cart-item-detail', kwargs={'pk': 99999}),
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cart_item_delete_not_found(self):
        """Test deleting non-existent cart item"""
        self.client.force_authenticate(self.user)

        response = self.client.delete(reverse('cart-item-detail', kwargs={'pk': 99999}))
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestWishlistAPIErrorHandling:
    """Test error handling paths for Wishlist APIs"""

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.product = ProductFactory()

    def test_wishlist_delete_not_found(self):
        """Test deleting non-existent wishlist item"""
        self.client.force_authenticate(self.user)

        response = self.client.delete(reverse('wishlist-delete', kwargs={'product_id': 99999}))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(response.data).lower()


@pytest.mark.django_db
class TestPermissionAPIErrorHandling:
    """Test error handling paths for Permission/Role APIs"""

    def setup_method(self):
        self.client = APIClient()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)

    def test_permission_detail_not_found(self):
        """Test accessing non-existent permission"""
        self.client.force_authenticate(self.admin_user)

        response = self.client.get(reverse('permission-detail', kwargs={'pk': 99999}))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_role_detail_not_found(self):
        """Test accessing non-existent role"""
        self.client.force_authenticate(self.admin_user)

        response = self.client.get(reverse('role-detail', kwargs={'pk': 99999}))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_role_assign_invalid_user(self):
        """Test assigning role to non-existent user"""
        from api.models import Role
        role = Role.objects.create(name='test_role')
        self.client.force_authenticate(self.admin_user)

        response = self.client.post(
            reverse('role-assign-user', kwargs={'role_pk': role.id, 'user_pk': 99999})
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_role_assign_invalid_role(self):
        """Test assigning non-existent role to user"""
        self.client.force_authenticate(self.admin_user)

        response = self.client.post(
            reverse('role-assign-user', kwargs={'role_pk': 99999, 'user_pk': self.admin_user.id})
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

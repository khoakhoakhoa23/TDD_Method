import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from api.models import Cart, CartItem, Order, OrderItem, Payment, Wishlist
from api.tests.factories import UserFactory, CategoryFactory, ProductFactory


@pytest.mark.django_db
class TestUserEcommerceJourney:
    """Test complete end-to-end user ecommerce journey"""

    def setup_method(self):
        self.client = APIClient()
        self.category = CategoryFactory(name="Electronics")
        self.product1 = ProductFactory(
            name="iPhone 15",
            price=1500000,
            stock=10,
            category=self.category
        )
        self.product2 = ProductFactory(
            name="Samsung Galaxy",
            price=1200000,
            stock=5,
            category=self.category
        )

    def test_complete_user_journey_register_to_purchase(self):
        """Test complete journey: register -> browse -> cart -> checkout -> payment"""

        # 1. User Registration
        register_data = {
            "username": "testuser123",
            "password": "password123"
        }
        response = self.client.post(reverse('register'), register_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['username'] == 'testuser123'

        # 2. User Login to get access token
        login_data = {
            "username": "testuser123",
            "password": "password123"
        }
        response = self.client.post(reverse('login'), login_data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # 3. Browse Products

        # 2. Browse Products
        response = self.client.get(reverse('product-list-create'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2

        # 3. Search Products
        response = self.client.get(reverse('product-list-create') + '?search=iPhone')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['name'] == "iPhone 15"

        # 4. Filter by Category
        response = self.client.get(
            reverse('product-list-create') + f'?category={self.category.id}'
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

        # 5. View Product Details
        response = self.client.get(
            reverse('product-detail', kwargs={'pk': self.product1.id})
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == "iPhone 15"
        assert response.data['price'] == 1500000

        # 6. Add to Wishlist
        wishlist_data = {"product_id": self.product1.id}
        response = self.client.post(reverse('wishlist-list-create'), wishlist_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        # 7. View Wishlist
        response = self.client.get(reverse('wishlist-list-create'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['product']['name'] == "iPhone 15"

        # 8. Add to Cart
        cart_data = {
            "product_id": self.product1.id,
            "quantity": 2
        }
        response = self.client.post(reverse('cart-view'), cart_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        # Add second product to cart
        cart_data2 = {
            "product_id": self.product2.id,
            "quantity": 1
        }
        response = self.client.post(reverse('cart-view'), cart_data2, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        # 9. View Cart
        response = self.client.get(reverse('cart-view'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['items']) == 2
        assert response.data['total'] == 4200000  # (1500000*2) + (1200000*1)

        # 10. Update Cart Item
        cart_item = CartItem.objects.filter(cart__user__username='testuser123').first()
        update_data = {"quantity": 1}
        response = self.client.put(
            reverse('cart-item-detail', kwargs={'pk': cart_item.id}),
            update_data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK

        # 11. Remove from Wishlist
        response = self.client.delete(
            reverse('wishlist-delete', kwargs={'product_id': self.product1.id})
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # 12. Checkout
        response = self.client.post(reverse('order-list-create'))
        assert response.status_code == status.HTTP_201_CREATED

        order_id = response.data['id']
        assert response.data['total'] == 2700000  # Updated cart total

        # 13. Create Payment
        payment_data = {"order_id": order_id, "provider": "vnpay"}
        response = self.client.post(reverse('create-payment'), payment_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        payment_id = response.data['payment_id']

        # 14. Check Payment Status
        response = self.client.get(reverse('payment-status', kwargs={'pk': payment_id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'pending'

        # 15. Simulate Payment Webhook
        webhook_data = {
            "transaction_id": response.data.get('transaction_id', 'TXN123'),
            "order_id": order_id,
            "status": "paid",
            "provider": "vnpay"
        }

        # Calculate webhook signature (simplified)
        import hmac
        import hashlib
        import json
        import time

        timestamp = str(int(time.time()))
        payload_str = json.dumps(webhook_data, separators=(',', ':'), sort_keys=True)
        message = f"{timestamp}.{payload_str}"
        secret = "dev-webhook-secret"
        signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        signature = f"sha256={signature}"

        webhook_client = APIClient()
        webhook_response = webhook_client.post(
            reverse('payment-webhook'),
            webhook_data,
            format='json',
            HTTP_X_WEBHOOK_TIMESTAMP=timestamp,
            HTTP_X_WEBHOOK_SIGNATURE=signature
        )
        assert webhook_response.status_code == status.HTTP_200_OK

        # 16. Verify Payment Status Updated
        response = self.client.get(reverse('payment-status', kwargs={'pk': payment_id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'paid'

        # 17. Verify Order Still Accessible (status not returned in detail API)
        response = self.client.get(reverse('order-detail', kwargs={'pk': order_id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == order_id

        # 18. Verify Cart is Empty After Checkout
        response = self.client.get(reverse('cart-view'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['items']) == 0

        # 19. Verify Stock Updated
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        assert self.product1.stock == 9  # 10 - 1
        assert self.product2.stock == 4  # 5 - 1


@pytest.mark.django_db
class TestAdminManagementJourney:
    """Test complete admin management journey"""

    def setup_method(self):
        self.client = APIClient()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_authenticate(self.admin_user)

    def test_admin_category_management_journey(self):
        """Test admin journey: create category -> create products -> manage inventory"""

        # 1. Create Category
        category_data = {"name": "Gaming Consoles"}
        response = self.client.post(reverse('category-list-create'), category_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        category_id = response.data['id']

        # 2. Create Products in Category
        product_data = {
            "name": "PlayStation 5",
            "price": 2000000,
            "stock": 20,
            "category": category_id
        }
        response = self.client.post(reverse('product-list-create'), product_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        product_id = response.data['id']

        # 3. Update Product
        update_data = {
            "name": "PlayStation 5 Digital Edition",
            "price": 1800000,
            "stock": 15,
            "category": category_id
        }
        response = self.client.put(
            reverse('product-detail', kwargs={'pk': product_id}),
            update_data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK

        # 4. View Statistics
        response = self.client.get(reverse('product-statistics'))
        assert response.status_code == status.HTTP_200_OK
        assert 'total_products' in response.data
        assert 'total_value' in response.data

        # 5. Create Permission
        perm_data = {"codename": "manage_inventory", "name": "Manage Inventory"}
        response = self.client.post(reverse('permissions-list-create'), perm_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        perm_id = response.data['id']

        # 6. Create Role with Permission
        role_data = {"name": "inventory_manager", "permissions": [perm_id]}
        response = self.client.post(reverse('roles-list-create'), role_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        role_id = response.data['id']

        # 7. Assign Role to User
        regular_user = UserFactory()
        response = self.client.post(
            reverse('role-assign-user', kwargs={'role_pk': role_id, 'user_pk': regular_user.id})
        )
        assert response.status_code == status.HTTP_200_OK

        # 8. Update Role
        update_role_data = {"name": "senior_inventory_manager", "permissions": [perm_id]}
        response = self.client.put(
            reverse('role-detail', kwargs={'pk': role_id}),
            update_role_data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK

        # 9. Delete Product
        response = self.client.delete(reverse('product-detail', kwargs={'pk': product_id}))
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # 10. Delete Category
        response = self.client.delete(reverse('category-detail', kwargs={'pk': category_id}))
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestConcurrentUserScenarios:
    """Test scenarios with multiple users interacting simultaneously"""

    def setup_method(self):
        self.client1 = APIClient()
        self.client2 = APIClient()
        self.product = ProductFactory(stock=5, price=1000)

        # Create two users
        self.user1 = UserFactory(username='user1')
        self.user2 = UserFactory(username='user2')

        # Authenticate both
        self.client1.force_authenticate(self.user1)
        self.client2.force_authenticate(self.user2)

    def test_concurrent_cart_operations(self):
        """Test both users adding same product to cart simultaneously"""

        # Both users add the same product to their carts
        cart_data = {"product_id": self.product.id, "quantity": 2}

        response1 = self.client1.post(reverse('cart-view'), cart_data, format='json')
        response2 = self.client2.post(reverse('cart-view'), cart_data, format='json')

        assert response1.status_code == status.HTTP_201_CREATED
        assert response2.status_code == status.HTTP_201_CREATED

        # Both should succeed since stock allows it
        self.product.refresh_from_db()
        assert self.product.stock == 5  # Stock unchanged until checkout

    def test_stock_race_condition_protection(self):
        """Test that stock management prevents overselling during concurrent checkouts"""

        # User 1 adds 3 items to cart
        cart_data1 = {"product_id": self.product.id, "quantity": 3}
        self.client1.post(reverse('cart-view'), cart_data1, format='json')

        # User 2 adds 3 items to cart (would exceed stock)
        cart_data2 = {"product_id": self.product.id, "quantity": 3}
        self.client2.post(reverse('cart-view'), cart_data2, format='json')

        # User 1 checkout first (should succeed)
        response1 = self.client1.post(reverse('order-list-create'))
        assert response1.status_code == status.HTTP_201_CREATED

        # User 2 checkout second (should fail due to insufficient stock)
        response2 = self.client2.post(reverse('order-list-create'))
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "checkout failed" in str(response2.data).lower()


@pytest.mark.django_db
class TestDataConsistencyJourney:
    """Test data consistency across related operations"""

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(self.user)

        self.product = ProductFactory(stock=10, price=1000)
        self.category = self.product.category

    def test_order_payment_data_consistency(self):
        """Test that order and payment data remain consistent throughout the flow"""

        # 1. Add to cart and checkout
        self.client.post(reverse('cart-view'), {
            "product_id": self.product.id,
            "quantity": 2
        }, format='json')

        response = self.client.post(reverse('order-list-create'))
        order_id = response.data['id']
        expected_total = 2000  # 2 * 1000

        # 2. Create payment
        payment_response = self.client.post(reverse('create-payment'), {
            "order_id": order_id,
            "provider": "vnpay"
        }, format='json')
        payment_id = payment_response.data['payment_id']

        # 3. Verify data consistency
        order_response = self.client.get(reverse('order-detail', kwargs={'pk': order_id}))
        payment_status_response = self.client.get(reverse('payment-status', kwargs={'pk': payment_id}))

        # Order total should match expected amount
        assert order_response.data['total'] == expected_total
        # Payment status should be pending initially
        assert payment_status_response.data['status'] == 'pending'

        # 4. Complete payment via webhook
        order_obj = Order.objects.get(id=order_id)
        webhook_data = {
            "transaction_id": payment_response.data.get('transaction_id', 'TXN123'),
            "order_id": order_id,
            "status": "paid",
            "provider": "vnpay"
        }

        # Calculate signature (simplified for test)
        import hmac, hashlib, json, time
        timestamp = str(int(time.time()))
        payload_str = json.dumps(webhook_data, separators=(',', ':'), sort_keys=True)
        message = f"{timestamp}.{payload_str}"
        signature = f"sha256={hmac.new('dev-webhook-secret'.encode(), message.encode(), hashlib.sha256).hexdigest()}"

        webhook_client = APIClient()
        webhook_client.post(
            reverse('payment-webhook'),
            webhook_data,
            format='json',
            HTTP_X_WEBHOOK_TIMESTAMP=timestamp,
            HTTP_X_WEBHOOK_SIGNATURE=signature
        )

        # 5. Verify final consistency
        order_response = self.client.get(reverse('order-detail', kwargs={'pk': order_id}))
        payment_status_response = self.client.get(reverse('payment-status', kwargs={'pk': payment_id}))

        # Order detail doesn't include status, just verify it's accessible
        assert order_response.data['id'] == order_id
        assert payment_status_response.data['status'] == 'paid'

        # 6. Verify stock updated correctly
        self.product.refresh_from_db()
        assert self.product.stock == 8  # 10 - 2

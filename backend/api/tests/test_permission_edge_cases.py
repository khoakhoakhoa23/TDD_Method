import pytest
from django.urls import reverse
from django.contrib.auth.models import AnonymousUser
from rest_framework import status
from rest_framework.test import APIClient

from api.models import Permission, Role
from api.permissions import user_has_permission, user_is_admin, IsAdminOrReadOnly
from api.tests.factories import UserFactory


@pytest.mark.django_db
class TestPermissionEdgeCases:
    """Test edge cases and boundary conditions for permission system"""

    def setup_method(self):
        self.client = APIClient()
        self.regular_user = UserFactory()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.anonymous_user = AnonymousUser()

        # Create permissions
        self.view_perm = Permission.objects.create(
            codename='view_reports',
            name='Can view reports'
        )
        self.edit_perm = Permission.objects.create(
            codename='edit_products',
            name='Can edit products'
        )

        # Create roles
        self.viewer_role = Role.objects.create(name='viewer')
        self.editor_role = Role.objects.create(name='editor')

        self.viewer_role.permissions.add(self.view_perm)
        self.editor_role.permissions.add(self.view_perm, self.edit_perm)

    def test_user_has_permission_none_user(self):
        """Test user_has_permission with None user"""
        assert not user_has_permission(None, 'view_reports')

    def test_user_has_permission_anonymous_user(self):
        """Test user_has_permission with anonymous user"""
        assert not user_has_permission(self.anonymous_user, 'view_reports')

    def test_user_has_permission_staff_user(self):
        """Test user_has_permission with staff user (should have all permissions)"""
        assert user_has_permission(self.admin_user, 'view_reports')
        assert user_has_permission(self.admin_user, 'nonexistent_permission')
        assert user_has_permission(self.admin_user, '')

    def test_user_has_permission_regular_user_no_roles(self):
        """Test user_has_permission with regular user having no roles"""
        assert not user_has_permission(self.regular_user, 'view_reports')
        assert not user_has_permission(self.regular_user, 'edit_products')

    def test_user_has_permission_user_with_role(self):
        """Test user_has_permission with user assigned to role"""
        self.regular_user.roles.add(self.viewer_role)

        assert user_has_permission(self.regular_user, 'view_reports')
        assert not user_has_permission(self.regular_user, 'edit_products')

    def test_user_has_permission_multiple_roles(self):
        """Test user_has_permission with user having multiple roles"""
        self.regular_user.roles.add(self.viewer_role, self.editor_role)

        assert user_has_permission(self.regular_user, 'view_reports')
        assert user_has_permission(self.regular_user, 'edit_products')

    def test_user_has_permission_invalid_codename(self):
        """Test user_has_permission with invalid codename"""
        self.regular_user.roles.add(self.viewer_role)

        assert not user_has_permission(self.regular_user, '')
        assert not user_has_permission(self.regular_user, None)

    def test_user_is_admin_none_user(self):
        """Test user_is_admin with None user"""
        assert not user_is_admin(None)

    def test_user_is_admin_anonymous_user(self):
        """Test user_is_admin with anonymous user"""
        assert not user_is_admin(self.anonymous_user)

    def test_user_is_admin_regular_user(self):
        """Test user_is_admin with regular user"""
        assert not user_is_admin(self.regular_user)

    def test_user_is_admin_staff_user(self):
        """Test user_is_admin with staff user"""
        assert user_is_admin(self.admin_user)

    def test_user_is_admin_superuser_only(self):
        """Test user_is_admin with superuser but not staff"""
        superuser_only = UserFactory(is_staff=False, is_superuser=True)
        assert not user_is_admin(superuser_only)


@pytest.mark.django_db
class TestIsAdminOrReadOnlyPermission:
    """Test IsAdminOrReadOnly permission class edge cases"""

    def test_has_permission_safe_methods_anonymous(self):
        """Test safe methods allowed for anonymous users"""
        permission = IsAdminOrReadOnly()
        mock_request = type('MockRequest', (), {'method': 'GET', 'user': AnonymousUser()})()
        mock_view = type('MockView', (), {})()

        assert permission.has_permission(mock_request, mock_view)

    def test_has_permission_safe_methods_authenticated(self):
        """Test safe methods allowed for authenticated users"""
        permission = IsAdminOrReadOnly()
        mock_user = UserFactory()
        mock_request = type('MockRequest', (), {'method': 'GET', 'user': mock_user})()
        mock_view = type('MockView', (), {})()

        assert permission.has_permission(mock_request, mock_view)

    def test_has_permission_unsafe_methods_anonymous(self):
        """Test unsafe methods denied for anonymous users"""
        permission = IsAdminOrReadOnly()
        mock_request = type('MockRequest', (), {'method': 'POST', 'user': AnonymousUser()})()
        mock_view = type('MockView', (), {})()

        assert not permission.has_permission(mock_request, mock_view)

    def test_has_permission_unsafe_methods_regular_user(self):
        """Test unsafe methods denied for regular users"""
        permission = IsAdminOrReadOnly()
        mock_user = UserFactory()
        mock_request = type('MockRequest', (), {'method': 'POST', 'user': mock_user})()
        mock_view = type('MockView', (), {})()

        assert not permission.has_permission(mock_request, mock_view)

    def test_has_permission_unsafe_methods_admin_user(self):
        """Test unsafe methods allowed for admin users"""
        permission = IsAdminOrReadOnly()
        mock_user = UserFactory(is_staff=True)
        mock_request = type('MockRequest', (), {'method': 'POST', 'user': mock_user})()
        mock_view = type('MockView', (), {})()

        assert permission.has_permission(mock_request, mock_view)

    def test_has_permission_head_method(self):
        """Test HEAD method treated as safe"""
        permission = IsAdminOrReadOnly()
        mock_user = UserFactory()
        mock_request = type('MockRequest', (), {'method': 'HEAD', 'user': mock_user})()
        mock_view = type('MockView', (), {})()

        assert permission.has_permission(mock_request, mock_view)

    def test_has_permission_options_method(self):
        """Test OPTIONS method treated as safe"""
        permission = IsAdminOrReadOnly()
        mock_user = UserFactory()
        mock_request = type('MockRequest', (), {'method': 'OPTIONS', 'user': mock_user})()
        mock_view = type('MockView', (), {})()

        assert permission.has_permission(mock_request, mock_view)


@pytest.mark.django_db
class TestAPIPermissionIntegration:
    """Test permission integration with actual API endpoints"""

    def setup_method(self):
        self.client = APIClient()
        self.regular_user = UserFactory()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)

        # Create test data
        from api.tests.factories import CategoryFactory, ProductFactory
        self.category = CategoryFactory()
        self.product = ProductFactory(category=self.category)

    def test_regular_user_can_read_products(self):
        """Test regular user can read products (GET requests)"""
        self.client.force_authenticate(self.regular_user)

        response = self.client.get(reverse('product-list-create'))
        assert response.status_code == status.HTTP_200_OK

        response = self.client.get(reverse('product-detail', kwargs={'pk': self.product.id}))
        assert response.status_code == status.HTTP_200_OK

    def test_regular_user_cannot_create_products(self):
        """Test regular user cannot create products (POST requests)"""
        self.client.force_authenticate(self.regular_user)

        data = {
            "name": "New Product",
            "price": 1000,
            "stock": 10,
            "category": self.category.id
        }

        response = self.client.post(reverse('product-list-create'), data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_regular_user_cannot_update_products(self):
        """Test regular user cannot update products (PUT requests)"""
        self.client.force_authenticate(self.regular_user)

        data = {"name": "Updated Product", "price": 2000, "stock": 20}

        response = self.client.put(
            reverse('product-detail', kwargs={'pk': self.product.id}),
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_regular_user_cannot_delete_products(self):
        """Test regular user cannot delete products (DELETE requests)"""
        self.client.force_authenticate(self.regular_user)

        response = self.client.delete(reverse('product-detail', kwargs={'pk': self.product.id}))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_user_can_create_products(self):
        """Test admin user can create products"""
        self.client.force_authenticate(self.admin_user)

        data = {
            "name": "Admin Product",
            "price": 5000,
            "stock": 50,
            "category": self.category.id
        }

        response = self.client.post(reverse('product-list-create'), data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_admin_user_can_update_products(self):
        """Test admin user can update products"""
        self.client.force_authenticate(self.admin_user)

        data = {"name": "Admin Updated", "price": 3000, "stock": 30}

        response = self.client.put(
            reverse('product-detail', kwargs={'pk': self.product.id}),
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_admin_user_can_delete_products(self):
        """Test admin user can delete products"""
        self.client.force_authenticate(self.admin_user)

        response = self.client.delete(reverse('product-detail', kwargs={'pk': self.product.id}))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_anonymous_user_can_read_products(self):
        """Test anonymous user can read products"""
        # Don't authenticate

        response = self.client.get(reverse('product-list-create'))
        assert response.status_code == status.HTTP_200_OK

    def test_anonymous_user_cannot_create_products(self):
        """Test anonymous user cannot create products"""
        # Don't authenticate

        data = {
            "name": "Anonymous Product",
            "price": 1000,
            "stock": 10,
            "category": self.category.id
        }

        response = self.client.post(reverse('product-list-create'), data, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_user_cannot_update_products(self):
        """Test anonymous user cannot update products"""
        # Don't authenticate

        data = {"name": "Anonymous Update", "price": 2000, "stock": 20}

        response = self.client.put(
            reverse('product-detail', kwargs={'pk': self.product.id}),
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_user_cannot_delete_products(self):
        """Test anonymous user cannot delete products"""
        # Don't authenticate

        response = self.client.delete(reverse('product-detail', kwargs={'pk': self.product.id}))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRolePermissionComplexScenarios:
    """Test complex role and permission scenarios"""

    def setup_method(self):
        self.client = APIClient()

        # Create permissions
        self.perm1 = Permission.objects.create(codename='read_data', name='Read Data')
        self.perm2 = Permission.objects.create(codename='write_data', name='Write Data')
        self.perm3 = Permission.objects.create(codename='delete_data', name='Delete Data')

        # Create roles
        self.role1 = Role.objects.create(name='reader')
        self.role2 = Role.objects.create(name='writer')
        self.role3 = Role.objects.create(name='admin')

        self.role1.permissions.add(self.perm1)
        self.role2.permissions.add(self.perm1, self.perm2)
        self.role3.permissions.add(self.perm1, self.perm2, self.perm3)

    def test_user_with_multiple_overlapping_roles(self):
        """Test user with multiple roles that have overlapping permissions"""
        user = UserFactory()
        user.roles.add(self.role1, self.role2)  # Both have read permission

        assert user_has_permission(user, 'read_data')
        assert user_has_permission(user, 'write_data')
        assert not user_has_permission(user, 'delete_data')

    def test_permission_revoked_when_role_removed(self):
        """Test permissions revoked when role is removed from user"""
        user = UserFactory()
        user.roles.add(self.role2)  # Has read and write

        assert user_has_permission(user, 'read_data')
        assert user_has_permission(user, 'write_data')

        # Remove role
        user.roles.remove(self.role2)

        assert not user_has_permission(user, 'read_data')
        assert not user_has_permission(user, 'write_data')

    def test_permission_granted_when_role_added(self):
        """Test permissions granted when role is added to user"""
        user = UserFactory()

        assert not user_has_permission(user, 'read_data')

        # Add role
        user.roles.add(self.role1)

        assert user_has_permission(user, 'read_data')

    def test_role_with_no_permissions(self):
        """Test role that has no permissions assigned"""
        empty_role = Role.objects.create(name='empty_role')
        user = UserFactory()
        user.roles.add(empty_role)

        assert not user_has_permission(user, 'read_data')
        assert not user_has_permission(user, 'write_data')
        assert not user_has_permission(user, 'delete_data')

    def test_permission_with_special_characters(self):
        """Test permissions with special characters in codename"""
        special_perm = Permission.objects.create(
            codename='special.permission:with:colons',
            name='Special Permission'
        )
        role = Role.objects.create(name='special_role')
        role.permissions.add(special_perm)
        user = UserFactory()
        user.roles.add(role)

        assert user_has_permission(user, 'special.permission:with:colons')

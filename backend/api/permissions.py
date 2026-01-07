from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrReadOnly(BasePermission):
    """
    Admin: full access
    User thường: read-only
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
            
        )


def user_has_permission(user, codename: str) -> bool:
    """Return True if the user has the given permission codename via roles or is staff."""
    if user is None:
        return False

    if not getattr(user, 'is_authenticated', False):
        return False

    if getattr(user, 'is_staff', False):
        return True

    # users may have related `roles` M2M from Role.users
    try:
        return user.roles.filter(permissions__codename=codename).exists()
    except Exception:
        return False

def user_is_admin(user) -> bool:
    """Return True if the user is staff (admin)."""
    if user is None:
        return False

    if not getattr(user, 'is_authenticated', False):
        return False

    return getattr(user, 'is_staff', False)

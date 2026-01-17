from django.urls import path

from .views import (
    # auth
    register,
    login_view,
    me,
    register_admin,

    # hello
    hello,

    # products
    product_list_create,
    product_detail,
    product_statistics,

    # categories
    category_list_create,
    category_detail,

    # cart
    cart_view,
    cart_item_detail,

    # wishlist
    wishlist_list_create,
    wishlist_item_delete,

    # orders
    orders_view,
    orders_detail,
    update_order_status,
    checkout_view,

    # payments
    create_payment,
    payment_webhook,
    get_payment_status,

    # permissions / roles
    permissions_list_create,
    permission_detail,
    roles_list_create,
    role_detail,
    role_assign_user,
)

urlpatterns = [
    # ===== HELLO =====
    path("hello/", hello, name="api-hello"),

    # ===== AUTH =====
    path("auth/register/", register, name="register"),
    path("auth/login/", login_view, name="login"),
    path("auth/me/", me, name="me"),
    path("auth/register-admin/", register_admin, name="register-admin"),

    # ===== PRODUCTS =====
    path("products/", product_list_create, name="product-list-create"),
    path("products/statistics/", product_statistics, name="product-statistics"),
    path("products/<int:pk>/", product_detail, name="product-detail"),

    # ===== CATEGORIES =====
    path("categories/", category_list_create, name="category-list-create"),
    path("categories/<int:pk>/", category_detail, name="category-detail"),

    # ===== CART =====
    path("cart/", cart_view, name="cart-view"),
    path("cart/items/<int:pk>/", cart_item_detail, name="cart-item-detail"),

    # ===== WISHLIST =====
    path("wishlist/", wishlist_list_create, name="wishlist-list-create"),
    path("wishlist/<int:product_id>/", wishlist_item_delete, name="wishlist-delete"),

    # ===== ORDERS =====
    path("orders/", orders_view, name="order-list-create"),
    path("orders/<int:pk>/", orders_detail, name="order-detail"),
    path("orders/<int:pk>/status/", update_order_status, name="update-order-status"),
    path("orders/<int:pk>/checkout/", checkout_view, name="checkout"),

    # ===== PAYMENTS (SPECIFIC → GENERIC) =====
    path("payments/<int:pk>/status/", get_payment_status, name="payment-status"),
    path("payments/webhook/", payment_webhook, name="payment-webhook"),
    path("payments/create/", create_payment, name="create-payment"),

    # ===== PERMISSIONS / ROLES =====
    path("permissions/", permissions_list_create, name="permissions-list-create"),
    path("permissions/<int:pk>/", permission_detail, name="permission-detail"),
    path("roles/", roles_list_create, name="roles-list-create"),
    path("roles/<int:pk>/", role_detail, name="role-detail"),
    path("roles/<int:role_pk>/users/<int:user_pk>/", role_assign_user, name="role-assign-user"),
    
]

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
    path("auth/register/", register),
    path("auth/login/", login_view),
    path("auth/me/", me),
    path("auth/register-admin/", register_admin),

    # ===== PRODUCTS =====
    path("products/", product_list_create),
    path("products/statistics/", product_statistics),
    path("products/<int:pk>/", product_detail),

    # ===== CATEGORIES =====
    path("categories/", category_list_create),
    path("categories/<int:pk>/", category_detail),

    # ===== CART =====
    path("cart/", cart_view),
    path("cart/items/<int:pk>/", cart_item_detail),

    # ===== ORDERS =====
    path("orders/", orders_view),
    path("orders/<int:pk>/", orders_detail),
    path("orders/<int:pk>/status/", update_order_status),
    path("orders/<int:pk>/checkout/", checkout_view),

    # ===== PAYMENTS (SPECIFIC → GENERIC) =====
    path("payments/<int:pk>/status/", get_payment_status),
    path("payments/webhook/", payment_webhook),
    path("payments/create/", create_payment),
    path("payments/", create_payment),

    # ===== PERMISSIONS / ROLES =====
    path("permissions/", permissions_list_create),
    path("permissions/<int:pk>/", permission_detail),
    path("roles/", roles_list_create),
    path("roles/<int:pk>/", role_detail),
    path("roles/<int:role_pk>/users/<int:user_pk>/", role_assign_user),
    
]

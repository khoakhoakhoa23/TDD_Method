from django.urls import path
from .views import me
from .views import hello, product_list_create,product_detail, category_list_create, category_detail
from .views import product_statistics
from .views import register, login_view
from .views import cart_view
from .views import cart_item_detail
from .views import orders_view, orders_detail
from .views import update_order_status
from .views import create_payment, payment_webhook
from .views import checkout_view
from .views import permissions_list_create, permission_detail, roles_list_create, role_detail, role_assign_user
from .views import register_admin



urlpatterns = [
    path('hello/', hello, name='api-hello'),
    path('products/', product_list_create),
    path('products/statistics/', product_statistics),
    path('products/<int:pk>/', product_detail),
    path('categories/', category_list_create),
    path('categories/<int:pk>/', category_detail),
    path('auth/register/', register),
    path('auth/login/', login_view),
    path('auth/me/', me),
    path('cart/', cart_view),
    path('cart/items/<int:pk>/', cart_item_detail),
    path('orders/', orders_view),
    path('orders/<int:pk>/', orders_detail),
    path("orders/<int:pk>/status/", update_order_status),
    path("orders/<int:pk>/checkout/", checkout_view),
    path("payments/create/", create_payment),
    path("payments/", create_payment),
    path("payments/webhook/", payment_webhook),
    path('permissions/', permissions_list_create),
    path('permissions/<int:pk>/', permission_detail),
    path('roles/', roles_list_create),
    path('roles/<int:pk>/', role_detail),
    path('roles/<int:role_pk>/users/<int:user_pk>/', role_assign_user),
    path('auth/register-admin/', register_admin),
    
    

    
   
    


]




import hashlib
import hmac
import json
import re
import time

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Avg, Count, F, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Cart,
    CartItem,
    Category,
    Order,
    OrderItem,
    Payment,
    Permission,
    Product,
    Role,
)
from .pagination import ProductPagination
from .permissions import IsAdminOrReadOnly, user_has_permission
from .serializers import (
    CartItemSerializer,
    CartSerializer,
    CategorySerializer,
    PermissionSerializer,
    ProductDetailSerializer,
    ProductSerializer,
    RoleSerializer,
)
from .throttles import CartRateThrottle, LoginRateThrottle, OrderRateThrottle

def json_error(message, status_code=status.HTTP_400_BAD_REQUEST):
    """Return a standardized JSON error response."""
    return Response({"error": message}, status=status_code)

PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_PAID = "paid"
PAYMENT_STATUS_FAILED = "failed"

PAYMENT_STATUS_MAP = {
    "paid": PAYMENT_STATUS_PAID,
    "success": PAYMENT_STATUS_PAID,
    "failed": PAYMENT_STATUS_FAILED,
}

WEBHOOK_SIGNATURE_HEADER = "X-Webhook-Signature"
WEBHOOK_TIMESTAMP_HEADER = "X-Webhook-Timestamp"


def _canonical_webhook_payload(data):
    if hasattr(data, "dict"):
        payload = data.dict()
    else:
        payload = data
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _verify_webhook_signature(request):
    secret = getattr(settings, "PAYMENT_WEBHOOK_SECRET", "")
    if not secret:
        return False, "Webhook secret not configured"

    timestamp = request.headers.get(WEBHOOK_TIMESTAMP_HEADER)
    signature = request.headers.get(WEBHOOK_SIGNATURE_HEADER)
    if not timestamp or not signature:
        return False, "Missing signature headers"

    try:
        timestamp_int = int(timestamp)
    except (TypeError, ValueError):
        return False, "Invalid signature timestamp"

    tolerance = getattr(settings, "PAYMENT_WEBHOOK_TOLERANCE_SECONDS", 300)
    now = int(time.time())
    if abs(now - timestamp_int) > tolerance:
        return False, "Signature timestamp expired"

    payload = _canonical_webhook_payload(request.data)
    signed_payload = f"{timestamp}.{payload}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()

    expected = f"sha256={digest}"
    if not (hmac.compare_digest(signature, expected) or hmac.compare_digest(signature, digest)):
        return False, "Invalid signature"

    return True, None


def _is_valid_payment_provider(provider):
    return provider in dict(Payment.PROVIDER_CHOICES)




# -------------------------
# TEST / HELLO API
# -------------------------
@api_view(['GET'])
def hello(request):
    return Response(
        {"message": "Hello from Django"},
        status=status.HTTP_200_OK
    )


# -------------------------
# PRODUCT: LIST + CREATE
# GET  /api/products/
# POST /api/products/
# -------------------------
@extend_schema(tags=['product'], summary='List or create products')
@api_view(['GET', 'POST'])
@permission_classes([IsAdminOrReadOnly])
def product_list_create(request):

    if request.method == 'GET':
        products = Product.objects.all()

        # category filter
        category_id = request.query_params.get('category')
        if category_id is not None and category_id != "":
            products = products.filter(category_id=category_id)

        # search filter (case-insensitive contains). An empty search returns all products.
        search = request.query_params.get('search')
        if search is not None:
            # Normalize whitespace and plus signs from query string
            search = search.replace('+', ' ').strip()
            if search != "":
                # Support multiple keywords (AND semantics): all keywords must appear in name
                keywords = [k for k in re.split(r"\s+", search) if k]
                for kw in keywords:
                    products = products.filter(name__icontains=kw)
      
        products = products.order_by('id')

        # Only apply pagination when the caller explicitly requests it via query params.
        paginator = ProductPagination()
        if 'page' in request.query_params or 'page_size' in request.query_params:
            page = paginator.paginate_queryset(products, request)
            if page is not None:
                serializer = ProductSerializer(page, many=True)
                # Return a plain list for compatibility with tests (they expect a list)
                return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            return Response(
                ProductSerializer(product).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# -------------------------
# PRODUCT: RETRIEVE + UPDATE + DELETE
# GET    /api/products/<id>/
# PUT    /api/products/<id>/
# DELETE /api/products/<id>/
# -------------------------
@extend_schema(tags=['product'], summary='Retrieve, update or delete a product')
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminOrReadOnly])
def product_detail(request, pk):

    # FIND PRODUCT
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return json_error("Product not found", status.HTTP_404_NOT_FOUND)

    # RETRIEVE PRODUCT
    if request.method == 'GET':
        serializer = ProductDetailSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # UPDATE PRODUCT
    if request.method == 'PUT':
        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            return Response(
                ProductSerializer(product).data,
                status=status.HTTP_200_OK
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # DELETE PRODUCT
    if request.method == 'DELETE':
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAdminOrReadOnly])
def category_list_create(request):

    if request.method == 'GET':
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            return Response(
                CategorySerializer(category).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminOrReadOnly])
def category_detail(request, pk):

    try:
        category = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        return json_error("Category not found", status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = CategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        serializer = CategorySerializer(category, data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            return Response(
                CategorySerializer(category).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

@api_view(['POST'])
@permission_classes([AllowAny])
@extend_schema(tags=['auth'], summary='Register a new user', description='Create a new user account. No authentication required.')
def register(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return json_error("Username and password required", status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return json_error("Username already exists", status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        username=username,
        password=password
    )

    return Response(
        {"id": user.id, "username": user.username},
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
@extend_schema(tags=['auth'], summary='Login and obtain JWT tokens', description='Provide `username` and `password` to receive `access` and `refresh` JWT tokens.')
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return json_error("Username and password required", status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    if user is None:
        return json_error("Invalid credentials", status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)
    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token)
    }, status=status.HTTP_200_OK)

@extend_schema(tags=['auth'], summary='Get current authenticated user', description='Requires Bearer JWT in Authorize. Returns `id` and `username`.')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    return Response(
        {"id": user.id, "username": user.username},
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def register_admin(request):
    """Create an admin (staff) user. Only callable by existing admin users."""
    username = request.data.get("username")
    password = request.data.get("password")
    make_super = bool(request.data.get("is_superuser", False))

    if not username or not password:
        return json_error("Username and password required", status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return json_error("Username already exists", status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        username=username,
        password=password,
    )
    user.is_staff = True
    if make_super:
        user.is_superuser = True
    user.save()

    return Response(
        {"id": user.id, "username": user.username, "is_staff": user.is_staff, "is_superuser": user.is_superuser},
        status=status.HTTP_201_CREATED
    )


@extend_schema(
    tags=['cart'],
    summary='Get or add items to cart',
    description='GET returns current cart; POST adds or updates a cart item.'
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([CartRateThrottle])
def cart_view(request):

    if request.method == 'GET':
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response({
                "id": None,
                "items": [],
                "total": 0,
                "user": request.user.id
            }, 200)
        return Response(CartSerializer(cart).data, 200)


    # ===================== POST =====================
    try:
        product_id = int(request.data.get('product_id'))
    except (TypeError, ValueError):
        return json_error("product_id must be a valid integer", 400)

    try:
        quantity = int(request.data.get('quantity', 0))
    except (TypeError, ValueError):
        return json_error("quantity must be a positive integer", 400)

    if quantity <= 0:
        return json_error("quantity must be a positive integer", 400)

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return json_error("Product not found", 404)

    if product.stock <= 0:
        return json_error("Not enough stock", 409)

    # 🔥 ALWAYS LOCK CART FIRST (fix deadlock!)
    for _ in range(3):
        try:
            with transaction.atomic():

                # Lock Cart row (prevent cart-level deadlock)
                cart = (
                    Cart.objects
                    .select_for_update()
                    .filter(user=request.user)
                    .first()
                )
                if not cart:
                    cart = Cart.objects.create(user=request.user)

                # Lock CartItem (ordered → no deadlock)
                cart_item = (
                    CartItem.objects
                    .select_for_update()
                    .filter(cart=cart, product=product)
                    .order_by("id")
                    .first()
                )

                if cart_item:
                    CartItem.objects.filter(id=cart_item.id).update(
                        quantity=F('quantity') + quantity
                    )
                    cart_item.refresh_from_db()
                else:
                    cart_item = CartItem.objects.create(
                        cart=cart,
                        product=product,
                        quantity=quantity
                    )

                Cart.objects.filter(id=cart.id).update(updated_at=timezone.now())

                return Response(
                    CartItemSerializer(cart_item).data,
                    status=201
                )

        except IntegrityError:
            continue

    return json_error("Concurrency conflict, please retry", 409)




@extend_schema(tags=['cart'], summary='Update or delete cart item')
@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([CartRateThrottle])
def cart_item_detail(request, pk):
    try:
        item = CartItem.objects.get(pk=pk, cart__user=request.user)
    except CartItem.DoesNotExist:
        return json_error("Cart item not found", status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        try:
            quantity = int(request.data.get("quantity", 0))
        except (TypeError, ValueError):
            return json_error("quantity must be a positive integer", 400)

        if quantity <= 0:
            return json_error("quantity must be a positive integer", 400)

        item.quantity = quantity
        item.save()
        Cart.objects.filter(id=item.cart_id).update(updated_at=timezone.now())
        return Response(
            CartItemSerializer(item).data,
            status=status.HTTP_200_OK
        )

    if request.method == 'DELETE':
        item.delete()
        Cart.objects.filter(id=item.cart_id).update(updated_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)

@extend_schema(tags=['cart'], summary='Get cart (alias)')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([CartRateThrottle])
def cart_get(request):
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        return Response({
            "id": None,
            "items": [],
            "total": 0,
            "user": request.user.id
        }, status=status.HTTP_200_OK)

    serializer = CartSerializer(cart)
    return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    tags=['order'],
    summary='List orders or checkout (create order)',
    description='GET: list user orders. POST: checkout cart → create order, decrease stock, clear cart.'
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([OrderRateThrottle])
def orders_view(request):

    # ===== GET: LIST ORDERS =====
    if request.method == "GET":
        orders = Order.objects.filter(user=request.user).order_by("-id")
        data = [
            {
                "id": order.id,
                "total": order.total,
                "items": [
                    {
                        "product_name": item.product_name,
                        "price": item.price,
                        "quantity": item.quantity
                    }
                    for item in order.items.all()
                ]
            }
            for order in orders
        ]
        return Response(data, 200)


    # ===== POST: CHECKOUT =====
    try:
        with transaction.atomic():
            # 1️⃣ LOCK CART + CARTITEMS THEO THỨ TỰ ỔN ĐỊNH
            cart = (
                Cart.objects
                .select_for_update()
                .filter(user=request.user)
                .first()
            )
            if not cart:
                return json_error("Cart is empty", 400)

            cart_items = (
                CartItem.objects
                .select_for_update()
                .filter(cart=cart)
                .order_by("id")            # 🔥 FIX DEADLOCK
            )

            if not cart_items.exists():
                return json_error("Cart is empty", 400)

            product_ids = list(cart_items.values_list("product_id", flat=True))
            products = (
                Product.objects
                .select_for_update()
                .filter(id__in=product_ids)
                .order_by("id")
            )
            product_map = {product.id: product for product in products}
            if len(product_map) != len(product_ids):
                return json_error("Product not found", 404)

            # 2️⃣ CREATE ORDER
            total = 0
            order = Order.objects.create(user=request.user, total=0)

            # 3️⃣ PROCESS ITEMS
            for item in cart_items:
                product = product_map[item.product_id]

                if product.stock < item.quantity:
                    raise IntegrityError("Not enough stock")

                Product.objects.filter(id=product.id).update(
                    stock=F('stock') - item.quantity
                )

                OrderItem.objects.create(
                    order=order,
                    product_name=product.name,
                    price=product.price,
                    quantity=item.quantity
                )

                total += product.price * item.quantity

            order.total = total
            order.save()

            # CLEAR CART
            cart_items.delete()
            Cart.objects.filter(id=cart.id).update(updated_at=timezone.now())

    except IntegrityError:
        return json_error("Checkout failed (concurrency/stock)", 400)
    except DatabaseError:
        return json_error("Checkout conflict, please retry", 409)

    # RESPONSE
    order_items = [
        {
            "product_name": oi.product_name,
            "price": oi.price,
            "quantity": oi.quantity
        }
        for oi in order.items.all()
    ]

    return Response(
        {"id": order.id, "total": order.total, "items": order_items},
        201
    )



@extend_schema(tags=['order'], summary='Retrieve order details')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([OrderRateThrottle])
def orders_detail(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return json_error("Order not found", status.HTTP_404_NOT_FOUND)

    # Only the owner, staff, or users with explicit permission can view the order
    if request.user != order.user and not (
        request.user.is_staff or user_has_permission(request.user, 'view_order')
    ):
        return json_error("You do not have permission to perform this action.", status.HTTP_403_FORBIDDEN)

    order_items = [
        {"product_name": oi.product_name, "price": oi.price, "quantity": oi.quantity}
        for oi in order.items.all()
    ]

    return Response({"id": order.id, "total": order.total, "items": order_items}, status=status.HTTP_200_OK)
@extend_schema(
    tags=['order'],
    summary='Checkout endpoint (not used)',
    description='Checkout is handled by POST /api/orders/. This endpoint exists only for routing compatibility.'
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([OrderRateThrottle])
def checkout_view(request, pk):
    return Response(
        {"detail": "Use POST /api/orders/ for checkout."},
        status=status.HTTP_200_OK
    )


@extend_schema(tags=['order'], summary='Update order status', description='Admin or authorized users may transition order status along allowed flow. Request body: {"status": "next_status"}.')
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_order_status(request, pk):
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return json_error("Order not found", status.HTTP_404_NOT_FOUND)

    # chỉ admin or role with permission
    if not (request.user.is_staff or user_has_permission(request.user, 'update_order_status')):
        return json_error("You do not have permission to perform this action.", status.HTTP_403_FORBIDDEN)

    new_status = request.data.get("status")

    # use string statuses so we don't depend on model constants
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_SHIPPED = "shipped"
    STATUS_COMPLETED = "completed"

    valid_flow = {
        STATUS_PENDING: STATUS_PAID,
        STATUS_PAID: STATUS_SHIPPED,
        STATUS_SHIPPED: STATUS_COMPLETED,
    }

    current_status = getattr(order, "status", STATUS_PENDING)

    if current_status not in valid_flow:
        return json_error("Order already completed", status.HTTP_400_BAD_REQUEST)

    if new_status != valid_flow[current_status]:
        return json_error("Invalid status transition", status.HTTP_400_BAD_REQUEST)

    # update if model supports it, otherwise return new status in response
    if hasattr(order, "status"):
        order.status = new_status
        order.save()

    response_status = getattr(order, "status", new_status)

    return Response({"id": order.id, "status": response_status}, status=status.HTTP_200_OK)


# -------------------------
# PERMISSIONS: LIST + CREATE
# -------------------------
@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def permissions_list_create(request):
    if request.method == 'GET':
        perms = Permission.objects.all()
        serializer = PermissionSerializer(perms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = PermissionSerializer(data=request.data)
    if serializer.is_valid():
        perm = serializer.save()
        return Response(PermissionSerializer(perm).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def permission_detail(request, pk):
    perm = get_object_or_404(Permission, pk=pk)

    if request.method == 'GET':
        return Response(PermissionSerializer(perm).data, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        serializer = PermissionSerializer(perm, data=request.data)
        if serializer.is_valid():
            perm = serializer.save()
            return Response(PermissionSerializer(perm).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    perm.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# -------------------------
# ROLES: LIST + CREATE
# -------------------------
@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def roles_list_create(request):
    if request.method == 'GET':
        roles = Role.objects.all()
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = RoleSerializer(data=request.data)
    if serializer.is_valid():
        role = serializer.save()
        return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def role_detail(request, pk):
    role = get_object_or_404(Role, pk=pk)

    if request.method == 'GET':
        return Response(RoleSerializer(role).data, status=status.HTTP_200_OK)

    if request.method == 'PUT':
        serializer = RoleSerializer(role, data=request.data)
        if serializer.is_valid():
            role = serializer.save()
            return Response(RoleSerializer(role).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    role.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST', 'DELETE'])
@permission_classes([IsAdminUser])
def role_assign_user(request, role_pk, user_pk):
    role = get_object_or_404(Role, pk=role_pk)
    user = get_object_or_404(User, pk=user_pk)

    if request.method == 'POST':
        role.users.add(user)
        return Response({'message': 'assigned'}, status=status.HTTP_200_OK)

    role.users.remove(user)
    return Response({'message': 'unassigned'}, status=status.HTTP_200_OK)


@api_view(['GET'])
def product_statistics(request):
    stats = Product.objects.aggregate(
        total_products=Count('id'),
        total_value=Sum('price'),
        average_price=Avg('price')
    )

    total_products = stats.get('total_products') or 0
    total_value = stats.get('total_value') or 0
    # ensure integer average for tests
    avg = stats.get('average_price')
    average_price = int(avg) if avg is not None else 0

    return Response({
        "total_products": total_products,
        "total_value": total_value,
        "average_price": average_price
    }, status=status.HTTP_200_OK)


@extend_schema(tags=['payment'], summary='Create payment for an order', description='Authenticated users call this to create a payment for their order; returns a `payment_url` and `transaction_id`. Provider must be one of the supported choices.')
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment(request):
    order_id = request.data.get("order_id")
    provider = request.data.get("provider")

    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        return json_error("order_id must be a valid integer", 400)

    if not provider:
        return json_error("provider is required", 400)
    if not _is_valid_payment_provider(provider):
        return json_error("Invalid payment provider", 400)

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if getattr(order, "status", None) == PAYMENT_STATUS_PAID:
        return json_error("Order already paid", 400)
    if Payment.objects.filter(order=order, status=PAYMENT_STATUS_PAID).exists():
        return json_error("Order already paid", 400)

    payment = Payment.objects.create(
        order=order,
        provider=provider,
        amount=order.total,
    )

    return Response(
        {
            "payment_id": payment.id,
            "transaction_id": payment.transaction_id,
            "payment_url": f"/mock-{provider}-pay/{payment.transaction_id}"
        },
        status=201
    )


@extend_schema(tags=['payment'], summary='Payment provider webhook', description='Called by external payment providers. Requires `X-Webhook-Timestamp` and `X-Webhook-Signature` (HMAC SHA256). Expects `transaction_id` (starts with "TXN"), `status`, and `order_id`. Idempotent. Side effects: creates/updates `Payment` and marks `Order` as paid/failed.')
@api_view(["POST"])
@permission_classes([AllowAny])
def payment_webhook(request):
    verified, error_message = _verify_webhook_signature(request)
    if not verified:
        return json_error(error_message, 400)

    transaction_id = request.data.get("transaction_id")
    status_value = request.data.get("status")  # success / failed
    order_id = request.data.get("order_id")

    # Simple validation: expected provider transaction IDs start with TXN
    if not transaction_id or not isinstance(transaction_id, str) or not transaction_id.startswith("TXN"):
        return json_error("Invalid transaction", 400)

    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        return json_error("order_id must be a valid integer", 400)

    if not status_value:
        return json_error("status is required", 400)

    normalized_status = PAYMENT_STATUS_MAP.get(str(status_value).lower())
    if normalized_status is None:
        return json_error("Invalid status", 400)

    provider = request.data.get("provider")
    if provider and not _is_valid_payment_provider(provider):
        return json_error("Invalid payment provider", 400)

    # perform DB updates in a transaction
    with transaction.atomic():
        # find or create payment for this transaction
        payment = Payment.objects.filter(transaction_id=transaction_id).first()

        if payment is None:
            # try to find order
            order = Order.objects.filter(id=order_id).first()
            if order is None:
                return json_error("Order not found", 400)

            # try to reuse an existing pending payment for the order (tests expect this)
            existing = Payment.objects.filter(order=order, status=PAYMENT_STATUS_PENDING).first()
            if existing is not None:
                payment = existing
                # attach transaction id to the existing payment
                payment.transaction_id = transaction_id
                update_fields = ["transaction_id"]
                if provider:
                    payment.provider = provider
                    update_fields.append("provider")
                payment.save(update_fields=update_fields)
            else:
                if not provider:
                    return json_error("provider is required", 400)
                payment = Payment.objects.create(
                    order=order,
                    provider=provider,
                    amount=order.total,
                    transaction_id=transaction_id,
                    status=PAYMENT_STATUS_PENDING,
                )

        # idempotency: if already paid, return OK
        if payment.status == PAYMENT_STATUS_PAID and normalized_status == PAYMENT_STATUS_PAID:
            return Response({"message": "Already processed"}, status=200)
        if payment.status == PAYMENT_STATUS_FAILED and normalized_status == PAYMENT_STATUS_FAILED:
            return Response({"message": "Already processed"}, status=200)
        if payment.status == PAYMENT_STATUS_PAID and normalized_status != PAYMENT_STATUS_PAID:
            return json_error("Payment already paid", 409)
        if payment.status == PAYMENT_STATUS_FAILED and normalized_status != PAYMENT_STATUS_FAILED:
            return json_error("Payment already failed", 409)

        if normalized_status == PAYMENT_STATUS_PAID:
            payment.status = PAYMENT_STATUS_PAID
            payment.save(update_fields=["status"])

            payment.order.status = PAYMENT_STATUS_PAID
            payment.order.save(update_fields=["status"])
        else:
            payment.status = PAYMENT_STATUS_FAILED
            payment.save(update_fields=["status"])

    return Response({"message": "Webhook processed"}, status=200)


class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

    def get_queryset(self):
        qs = Product.objects.all()
        request = self.request

        query = request.query_params.get("q", "")
        query = query.strip()

        # whitespace or empty -> return all
        if not query:
            return qs

        # long query fallback
        if len(query) > 100:
            return qs

        # multiple keywords
        keywords = query.split()

        for kw in keywords:
            qs = qs.filter(name__icontains=kw)

        return qs
    

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_payment_status(request, pk):
    payment = get_object_or_404(
        Payment,
        id=pk,
        order__user=request.user   
    )

    return Response(
        {
            "id": payment.id,
            "status": payment.status
        },
        status=status.HTTP_200_OK
    )



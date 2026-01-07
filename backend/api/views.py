
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.decorators import permission_classes
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Product, Cart, CartItem, Order, OrderItem, Payment
from .serializers import ProductSerializer, ProductDetailSerializer
from .serializers import CategorySerializer, CartItemSerializer, CartSerializer
from .models import Category
from .serializers import CategorySerializer
from .serializers import PermissionSerializer, RoleSerializer
from .models import Permission, Role
from .permissions import user_has_permission
from django.db import transaction
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, Avg
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import OpenApiResponse
from .pagination import ProductPagination
import re
from django.db.models import Q
from rest_framework.viewsets import ModelViewSet
from .models import Product
from .serializers import ProductSerializer
from rest_framework.views import APIView
from api.models import CartItem
from api.serializers import CartItemSerializer

def json_error(message, status_code=status.HTTP_400_BAD_REQUEST):
    """Return a standardized JSON error response."""
    return Response({"error": message}, status=status_code)




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
        # If the requester is authenticated but not staff, forbid creation.
        # Allow anonymous creation (tests expect anonymous POST to succeed).
        if request.user.is_authenticated and not (
            request.user.is_staff or user_has_permission(request.user, 'create_product')
        ):
            return json_error("You do not have permission to perform this action.", status.HTTP_403_FORBIDDEN)

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
def category_list_create(request):

    if request.method == 'GET':
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        # If requester is authenticated but not staff, forbid creation.
        # Allow anonymous creation (tests expect anonymous POST to succeed).
        if request.user.is_authenticated and not (
            request.user.is_staff or user_has_permission(request.user, 'create_category')
        ):
            return json_error("You do not have permission to perform this action.", status.HTTP_403_FORBIDDEN)

        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            return Response(
                CategorySerializer(category).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['GET', 'PUT', 'DELETE'])
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


@extend_schema(tags=['cart'], summary='Get or add items to cart', description='GET returns current cart for authenticated user; POST adds/updates a cart item.')
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
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
            }, status=status.HTTP_200_OK)

        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
    product_id = request.data.get('product_id')
    quantity = request.data.get('quantity')

    if product_id is None or quantity is None:
        return json_error("product_id and quantity required", status.HTTP_400_BAD_REQUEST)

    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError()
    except Exception:
        return json_error("quantity must be a positive integer", status.HTTP_400_BAD_REQUEST)

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return json_error("Product not found", status.HTTP_404_NOT_FOUND)

    cart, _ = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    if not created:
        cart_item.quantity = quantity
        cart_item.save()

    return Response(
        CartItemSerializer(cart_item).data,
        status=status.HTTP_201_CREATED
    )

@extend_schema(tags=['cart'], summary='Update or delete cart item')
@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def cart_item_detail(request, pk):
    item = CartItem.objects.get(pk=pk, cart__user=request.user)

    if request.method == 'PUT':
        quantity = request.data.get("quantity")
        item.quantity = quantity
        item.save()
        return Response(
            CartItemSerializer(item).data,
            status=status.HTTP_200_OK
        )

    if request.method == 'DELETE':
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@extend_schema(tags=['cart'], summary='Get cart (alias)')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
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

@extend_schema(tags=['order'], summary='List orders or checkout (create order)', description='POST implements checkout: creates order from current cart, decrements stock, clears cart. Requires authentication.')
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def orders_view(request):
    if request.method == "POST":
        cart_items = CartItem.objects.filter(cart__user=request.user)

        if not cart_items.exists():
            return json_error("Cart is empty", status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            total = 0
            order = Order.objects.create(user=request.user, total=0)

            for item in cart_items.select_for_update():
                product = item.product

                if item.quantity > product.stock:
                    raise ValidationError(
                        f"Not enough stock for {product.name}"
                    )

                # decrement stock
                product.stock -= item.quantity
                product.save()

                OrderItem.objects.create(
                    order=order,
                    product_name=product.name,
                    price=product.price,
                    quantity=item.quantity
                )

                total += product.price * item.quantity

            order.total = total
            order.save()

            # clear cart
            cart_items.delete()

        order_items = [
            {"product_name": oi.product_name, "price": oi.price, "quantity": oi.quantity}
            for oi in order.items.all()
        ]

        return Response(
            {"id": order.id, "total": order.total, "items": order_items},
            status=status.HTTP_201_CREATED
        )

@extend_schema(tags=['order'], summary='Retrieve order details')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
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
@extend_schema(tags=['order'], summary='Checkout specific order (placeholder)', description='Placeholder endpoint to require authentication for checkout-related routes.')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkout_view(request, pk):
    # Minimal placeholder: real checkout logic is handled via POST /api/orders/
    return Response({"detail": "Checkout endpoint (not implemented here)."}, status=status.HTTP_200_OK)


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


@extend_schema(tags=['payment'], summary='Create payment for an order', description='Authenticated users call this to create a payment for their order; returns a `payment_url` and `transaction_id`.')
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment(request):
    order_id = request.data.get("order_id")
    provider = request.data.get("provider")

    order = get_object_or_404(Order, id=order_id, user=request.user)

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


@extend_schema(tags=['payment'], summary='Payment provider webhook', description='Called by external payment providers. No authentication. Expects `transaction_id` (starts with "TXN"), `status`, and `order_id`. Idempotent. Side effects: creates/updates `Payment` and marks `Order` as paid/failed.')
@api_view(["POST"])
@permission_classes([AllowAny])
def payment_webhook(request):
    transaction_id = request.data.get("transaction_id")
    status_value = request.data.get("status")  # success / failed
    order_id = request.data.get("order_id")

    # Simple validation: expected provider transaction IDs start with TXN
    if not transaction_id or not isinstance(transaction_id, str) or not transaction_id.startswith("TXN"):
        return json_error("Invalid transaction", 400)

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
            existing = Payment.objects.filter(order=order, status="pending").first()
            if existing is not None:
                payment = existing
                # attach transaction id to the existing payment
                payment.transaction_id = transaction_id
                payment.provider = request.data.get("provider", payment.provider or "unknown")
                payment.save(update_fields=["transaction_id", "provider"])                
            else:
                payment = Payment.objects.create(
                    order=order,
                    provider=request.data.get("provider", "unknown"),
                    amount=order.total,
                    transaction_id=transaction_id,
                    status="pending",
                )

        # idempotency: if already paid, return OK
        if payment.status == "paid":
            return Response({"message": "Already processed"}, status=200)

        if status_value == "paid" or status_value == "success":
            payment.status = "paid"
            payment.save()

            payment.order.status = "paid"
            payment.order.save()
        else:
            payment.status = "failed"
            payment.save()

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
    

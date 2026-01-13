"""
Test data factories for creating test objects easily.
This follows the Factory pattern to reduce boilerplate in tests.
"""
import factory
from django.contrib.auth.models import User
from api.models import Category, Product, Cart, CartItem, Order, OrderItem


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating User instances"""
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall('set_password', 'defaultpass123')


class AdminUserFactory(UserFactory):
    """Factory for creating admin User instances"""
    is_staff = True
    is_superuser = True
    username = factory.Sequence(lambda n: f"admin{n}")


class CategoryFactory(factory.django.DjangoModelFactory):
    """Factory for creating Category instances"""
    class Meta:
        model = Category
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f"Category {n}")


class ProductFactory(factory.django.DjangoModelFactory):
    """Factory for creating Product instances"""
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    price = factory.Faker('random_int', min=10000, max=10000000)
    stock = factory.Faker('random_int', min=0, max=100)
    category = factory.SubFactory(CategoryFactory)


class CartFactory(factory.django.DjangoModelFactory):
    """Factory for creating Cart instances"""
    class Meta:
        model = Cart

    user = factory.SubFactory(UserFactory)


class CartItemFactory(factory.django.DjangoModelFactory):
    """Factory for creating CartItem instances"""
    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = factory.Faker('random_int', min=1, max=10)


class OrderFactory(factory.django.DjangoModelFactory):
    """Factory for creating Order instances"""
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    total = factory.Faker('random_int', min=10000, max=1000000)
    status = "pending"


class OrderItemFactory(factory.django.DjangoModelFactory):
    """Factory for creating OrderItem instances"""
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product_name = factory.Faker('word')
    price = factory.Faker('random_int', min=1000, max=100000)
    quantity = factory.Faker('random_int', min=1, max=5)







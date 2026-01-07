from django.db import models
from django.conf import settings
import uuid


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.IntegerField()
    stock = models.IntegerField()
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart"
    )

    def __str__(self):
        return f"Cart of {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"
    
class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total = models.IntegerField()
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_name = models.CharField(max_length=255)
    price = models.IntegerField()
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return self.product_name


        return f"Order {self.id}"

class Payment(models.Model):
    PROVIDER_CHOICES = [
        ("vnpay", "VNPay"),
        ("momo", "MoMo"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
        related_name="payments"
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    amount = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    transaction_id = models.CharField(max_length=100, default=uuid.uuid4, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)


class Permission(models.Model):
    codename = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.codename


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="roles",
        blank=True,
    )

    def __str__(self):
        return self.name


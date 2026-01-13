from rest_framework.throttling import ScopedRateThrottle


class LoginRateThrottle(ScopedRateThrottle):
    scope = "login"


class CartRateThrottle(ScopedRateThrottle):
    scope = "cart"


class OrderRateThrottle(ScopedRateThrottle):
    scope = "order"

class PaymentRateThrottle(ScopedRateThrottle):
    scope = "payment"

class WebhookRateThrottle(ScopedRateThrottle):
    scope = "webhook"
class ProductRateThrottle(ScopedRateThrottle):
    scope = "product"   
class CategoryRateThrottle(ScopedRateThrottle):
    scope = "category"

# Hướng dẫn Test-Driven Development (TDD) cho TMDT Project

## 📚 Tổng quan về TDD

**Test-Driven Development (TDD)** là một phương pháp phát triển phần mềm trong đó bạn viết test trước khi viết code. Quy trình TDD gồm 3 bước:

### 🔴 RED → 🟢 GREEN → 🔵 REFACTOR

1. **RED (Đỏ)**: Viết test cho tính năng mới → Test sẽ fail vì chưa có code
2. **GREEN (Xanh)**: Viết code tối thiểu để test pass
3. **REFACTOR (Tái cấu trúc)**: Cải thiện code mà vẫn giữ test pass

## 🎯 Lợi ích của TDD

- ✅ Code chất lượng cao hơn
- ✅ Ít bug hơn
- ✅ Dễ refactor
- ✅ Documentation sống (tests là documentation)
- ✅ Tự tin khi thay đổi code

## 📋 Quy trình TDD trong dự án này

### Bước 1: Viết Test (RED)

```python
# backend/api/tests/test_new_feature.py
import pytest
from rest_framework.test import APIClient
from api.models import Product

@pytest.mark.django_db
def test_create_product_with_validation():
    """Test: Tạo sản phẩm với validation"""
    client = APIClient()
    
    # Test case: Tạo sản phẩm với giá âm → phải fail
    data = {
        "name": "Test Product",
        "price": -1000,  # Giá âm không hợp lệ
        "stock": 10
    }
    
    response = client.post("/api/products/", data, format="json")
    
    # Assert: Phải trả về 400 Bad Request
    assert response.status_code == 400
    assert "price" in response.data  # Error về price
```

**Chạy test:**
```bash
cd backend
pytest api/tests/test_new_feature.py::test_create_product_with_validation -v
```

**Kết quả:** Test sẽ FAIL (RED) vì chưa có validation logic.

### Bước 2: Viết Code (GREEN)

```python
# backend/api/serializers.py
class ProductSerializer(serializers.ModelSerializer):
    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price must be positive")
        return value
```

**Chạy lại test:**
```bash
pytest api/tests/test_new_feature.py::test_create_product_with_validation -v
```

**Kết quả:** Test PASS (GREEN) ✅

### Bước 3: Refactor (nếu cần)

Cải thiện code mà vẫn giữ test pass:
- Tối ưu performance
- Cải thiện readability
- Extract methods/classes

## 🏗️ Cấu trúc Test trong dự án

```
backend/
├── api/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # Shared fixtures
│   │   ├── factories.py         # Test data factories
│   │   ├── test_auth_api.py     # Authentication tests
│   │   ├── test_product_api.py  # Product CRUD tests
│   │   ├── test_cart_api.py     # Cart tests
│   │   ├── test_order_api.py    # Order tests
│   │   └── test_payment_api.py  # Payment tests
```

## 🛠️ Best Practices

### 1. Test Naming Convention

```python
# ✅ GOOD: Mô tả rõ ràng test case
def test_user_cannot_create_product_without_permission():
    pass

def test_checkout_creates_order_and_clears_cart():
    pass

# ❌ BAD: Tên không rõ ràng
def test_product():
    pass

def test_1():
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
@pytest.mark.django_db
def test_add_product_to_cart():
    # ARRANGE: Setup test data
    user = User.objects.create_user(username="test", password="pass")
    product = Product.objects.create(name="Test", price=1000, stock=10)
    client = APIClient()
    client.force_authenticate(user=user)
    
    # ACT: Perform action
    response = client.post("/api/cart/", {
        "product_id": product.id,
        "quantity": 2
    }, format="json")
    
    # ASSERT: Verify result
    assert response.status_code == 201
    assert response.data["quantity"] == 2
```

### 3. Test Isolation

Mỗi test phải độc lập, không phụ thuộc vào test khác:

```python
@pytest.mark.django_db  # Mỗi test có database riêng
def test_isolated_test():
    # Test này không ảnh hưởng đến test khác
    pass
```

### 4. Use Fixtures

```python
# conftest.py
@pytest.fixture
def authenticated_client():
    user = User.objects.create_user(username="test", password="pass")
    client = APIClient()
    client.force_authenticate(user=user)
    return client

# test_file.py
def test_something(authenticated_client):
    response = authenticated_client.get("/api/cart/")
    assert response.status_code == 200
```

### 5. Test Edge Cases

```python
# Test với dữ liệu hợp lệ
def test_create_product_with_valid_data():
    pass

# Test với dữ liệu không hợp lệ
def test_create_product_with_negative_price():
    pass

# Test với dữ liệu thiếu
def test_create_product_without_name():
    pass

# Test với dữ liệu boundary
def test_create_product_with_zero_stock():
    pass
```

## 📊 Test Coverage

Mục tiêu: **Coverage > 80%**

Chạy coverage:
```bash
pytest --cov=api --cov-report=html
```

Xem report:
```bash
# Mở file htmlcov/index.html trong browser
```

## 🚀 Workflow TDD cho tính năng mới

### Ví dụ: Thêm tính năng "Product Reviews"

#### Step 1: Viết Test (RED)

```python
# test_review_api.py
@pytest.mark.django_db
def test_user_can_create_review():
    user = User.objects.create_user(username="test", password="pass")
    product = Product.objects.create(name="Test", price=1000, stock=10)
    client = APIClient()
    client.force_authenticate(user=user)
    
    response = client.post(f"/api/products/{product.id}/reviews/", {
        "rating": 5,
        "comment": "Great product!"
    }, format="json")
    
    assert response.status_code == 201
    assert response.data["rating"] == 5
```

**Chạy test → FAIL (RED)** ✅

#### Step 2: Viết Model

```python
# models.py
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
```

#### Step 3: Viết Serializer

```python
# serializers.py
class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'rating', 'comment', 'user', 'created_at']
```

#### Step 4: Viết View

```python
# views.py
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review(request, pk):
    product = get_object_or_404(Product, pk=pk)
    serializer = ReviewSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(product=product, user=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
```

#### Step 5: Chạy lại test → PASS (GREEN) ✅

#### Step 6: Refactor (nếu cần)

## 📝 Checklist khi viết test

- [ ] Test có tên mô tả rõ ràng
- [ ] Test độc lập (không phụ thuộc test khác)
- [ ] Test cả happy path và edge cases
- [ ] Test validation errors
- [ ] Test permissions (unauthorized, forbidden)
- [ ] Test với dữ liệu hợp lệ và không hợp lệ
- [ ] Test boundary values (0, -1, max, etc.)

## 🔧 Commands hữu ích

```bash
# Chạy tất cả tests
pytest

# Chạy test cụ thể
pytest api/tests/test_product_api.py

# Chạy test với verbose
pytest -v

# Chạy test và xem coverage
pytest --cov=api --cov-report=term-missing

# Chạy test và stop ở lỗi đầu tiên
pytest -x

# Chạy test và hiển thị print statements
pytest -s

# Chạy test theo pattern
pytest -k "test_product"

# Chạy test và tạo HTML coverage report
pytest --cov=api --cov-report=html
```

## 📚 Tài liệu tham khảo

- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [TDD Best Practices](https://testdriven.io/blog/testing-best-practices/)

## 🎓 Ví dụ thực tế

Xem các test files trong `backend/api/tests/` để học cách áp dụng TDD:

- `test_product_api.py` - Product CRUD với TDD
- `test_cart_api.py` - Cart operations với TDD
- `test_order_api.py` - Order flow với TDD

---

**Lưu ý:** Luôn viết test trước khi viết code mới! 🔴 → 🟢 → 🔵





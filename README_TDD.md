# TMDT Project - Test-Driven Development (TDD)

## 📋 Tổng quan

Dự án này được phát triển theo phương pháp **Test-Driven Development (TDD)**, đảm bảo code chất lượng cao và dễ maintain.

## 🎯 TDD Workflow

### Quy trình 3 bước: RED → GREEN → REFACTOR

1. **🔴 RED**: Viết test trước → Test sẽ fail vì chưa có code
2. **🟢 GREEN**: Viết code tối thiểu để test pass
3. **🔵 REFACTOR**: Cải thiện code mà vẫn giữ test pass

## 📚 Tài liệu

- **[TDD_GUIDE.md](./TDD_GUIDE.md)** - Hướng dẫn chi tiết về TDD
- **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** - Hướng dẫn testing và sử dụng fixtures

## 🚀 Quick Start

### 1. Cài đặt dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Chạy tests

```bash
# Chạy tất cả tests
pytest

# Chạy với coverage
pytest --cov=api --cov-report=html

# Chạy test cụ thể
pytest api/tests/test_product_api.py -v
```

### 3. Xem coverage report

Sau khi chạy coverage, mở file `htmlcov/index.html` trong browser.

## 📁 Cấu trúc Test

```
backend/api/tests/
├── __init__.py
├── conftest.py                      # Shared fixtures
├── factories.py                     # Test data factories
├── test_auth_api.py                 # Authentication tests
├── test_product_api.py              # Product CRUD (original)
├── test_product_api_refactored.py   # Product CRUD (using fixtures)
├── test_product_validation_tdd.py   # Product validation (TDD example)
├── test_product_search_tdd.py       # Product search (TDD example)
├── test_example_tdd_workflow.py     # Complete TDD workflow example
├── test_category_api.py             # Category tests
├── test_cart_api.py                 # Cart tests
├── test_order_api.py                # Order tests
└── test_payment_api.py              # Payment tests
```

## 🛠️ Fixtures & Factories

### Sử dụng Fixtures

```python
def test_example(api_client, user, product, authenticated_client):
    # api_client: Basic APIClient
    # user: Test user
    # product: Test product with category
    # authenticated_client: Authenticated APIClient
    response = authenticated_client.get(f"/api/products/{product.id}/")
    assert response.status_code == 200
```

### Sử dụng Factories

```python
from api.tests.factories import ProductFactory, UserFactory

def test_with_factory():
    product = ProductFactory(name="Custom", price=100000)
    user = UserFactory(username="testuser")
```

## 📊 Test Coverage

**Mục tiêu**: Coverage > 80%

```bash
# Generate coverage report
pytest --cov=api --cov-report=html --cov-report=term-missing

# View report
# Mở htmlcov/index.html trong browser
```

## ✅ Best Practices

### 1. Viết test trước khi viết code

```python
# ✅ GOOD: Test trước
def test_new_feature(api_client):
    response = api_client.get("/api/new-endpoint/")
    assert response.status_code == 200

# ❌ BAD: Code trước, test sau
```

### 2. Test naming

```python
# ✅ GOOD: Tên mô tả rõ ràng
def test_user_cannot_create_product_without_permission():
    pass

# ❌ BAD: Tên không rõ ràng
def test_product():
    pass
```

### 3. Test isolation

```python
@pytest.mark.django_db  # Mỗi test có database riêng
def test_isolated():
    # Test này không ảnh hưởng test khác
    pass
```

### 4. Arrange-Act-Assert pattern

```python
@pytest.mark.django_db
def test_example(api_client, product):
    # ARRANGE: Setup (từ fixtures)
    
    # ACT: Perform action
    response = api_client.get(f"/api/products/{product.id}/")
    
    # ASSERT: Verify result
    assert response.status_code == 200
    assert response.data["name"] == product.name
```

## 🎓 Ví dụ TDD Workflow

### Ví dụ: Thêm tính năng Product Statistics

#### Step 1: RED - Viết test

```python
@pytest.mark.django_db
def test_get_product_statistics(api_client, multiple_products):
    response = api_client.get("/api/products/statistics/")
    
    assert response.status_code == 200
    assert "total_products" in response.data
    assert response.data["total_products"] == 5
```

**Chạy test → FAIL (RED)** ✅

#### Step 2: GREEN - Implement code

```python
# views.py
@api_view(['GET'])
def product_statistics(request):
    products = Product.objects.all()
    return Response({
        "total_products": products.count(),
        "total_value": sum(p.price for p in products),
        "average_price": sum(p.price for p in products) / products.count() if products.count() > 0 else 0
    })
```

**Chạy lại test → PASS (GREEN)** ✅

#### Step 3: REFACTOR - Cải thiện code

```python
# views.py - Sử dụng aggregation
from django.db.models import Count, Sum, Avg

@api_view(['GET'])
def product_statistics(request):
    stats = Product.objects.aggregate(
        total_products=Count('id'),
        total_value=Sum('price'),
        average_price=Avg('price')
    )
    return Response({
        "total_products": stats['total_products'] or 0,
        "total_value": stats['total_value'] or 0,
        "average_price": stats['average_price'] or 0
    })
```

**Chạy lại test → Vẫn PASS** ✅

## 📝 Checklist khi viết test

- [ ] Test có tên mô tả rõ ràng
- [ ] Test độc lập (không phụ thuộc test khác)
- [ ] Sử dụng `@pytest.mark.django_db` cho DB operations
- [ ] Test cả happy path và edge cases
- [ ] Test validation errors
- [ ] Test permissions (unauthorized, forbidden)
- [ ] Test với dữ liệu hợp lệ và không hợp lệ
- [ ] Test boundary values

## 🔧 Commands hữu ích

```bash
# Chạy tất cả tests
pytest

# Chạy với verbose
pytest -v

# Chạy và stop ở lỗi đầu tiên
pytest -x

# Chạy test cụ thể
pytest api/tests/test_product_api.py::test_create_product

# Chạy test theo pattern
pytest -k "product"

# Chạy với coverage
pytest --cov=api --cov-report=html

# Chạy với print statements
pytest -s
```

## 📚 Tài liệu tham khảo

- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [TDD Best Practices](https://testdriven.io/blog/testing-best-practices/)

## 🎯 Mục tiêu

- ✅ Coverage > 80%
- ✅ Tất cả tests pass
- ✅ Code quality cao
- ✅ Dễ maintain và extend

---

**Remember: RED → GREEN → REFACTOR** 🔴 → 🟢 → 🔵





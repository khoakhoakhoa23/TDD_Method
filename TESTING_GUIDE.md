# Hướng dẫn Testing cho TMDT Project

## 🚀 Quick Start

### Cài đặt dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Chạy tests

```bash
# Chạy tất cả tests
pytest

# Chạy với verbose output
pytest -v

# Chạy test cụ thể
pytest api/tests/test_product_api.py

# Chạy test với coverage
pytest --cov=api --cov-report=html
```

## 📁 Cấu trúc Test Files

```
backend/api/tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── factories.py                   # Test data factories
├── test_auth_api.py              # Authentication tests
├── test_product_api.py           # Product CRUD (original)
├── test_product_api_refactored.py # Product CRUD (using fixtures)
├── test_product_validation_tdd.py # Product validation (TDD)
├── test_product_search_tdd.py    # Product search (TDD)
├── test_category_api.py          # Category tests
├── test_cart_api.py              # Cart tests
├── test_order_api.py             # Order tests
└── test_payment_api.py           # Payment tests
```

## 🎯 Sử dụng Fixtures

### Basic Fixtures (từ conftest.py)

```python
def test_example(api_client, user, product):
    # api_client: APIClient không cần auth
    # user: User object
    # product: Product object với category
    response = api_client.get(f"/api/products/{product.id}/")
    assert response.status_code == 200
```

### Authentication Fixtures

```python
def test_authenticated_endpoint(authenticated_client):
    # authenticated_client: APIClient đã login với user thường
    response = authenticated_client.get("/api/cart/")
    assert response.status_code == 200

def test_admin_endpoint(admin_client):
    # admin_client: APIClient đã login với admin
    response = admin_client.post("/api/products/", {...})
    assert response.status_code == 201
```

### Multiple Objects Fixtures

```python
def test_list_products(api_client, multiple_products):
    # multiple_products: List of 5 products
    response = api_client.get("/api/products/")
    assert len(response.data) == 5
```

## 🏭 Sử dụng Factories

Factories giúp tạo test data dễ dàng hơn:

```python
from api.tests.factories import ProductFactory, CategoryFactory, UserFactory

def test_with_factory():
    # Tạo product với factory
    product = ProductFactory(name="Custom Product", price=100000)
    
    # Tạo multiple products
    products = ProductFactory.create_batch(5)
    
    # Tạo user với factory
    user = UserFactory(username="testuser")
```

## 📝 Viết Test mới theo TDD

### Bước 1: Viết Test (RED)

```python
# test_new_feature.py
@pytest.mark.django_db
def test_new_feature(api_client):
    response = api_client.get("/api/new-endpoint/")
    assert response.status_code == 200
```

**Chạy test → FAIL (RED)** ✅

### Bước 2: Implement Code (GREEN)

```python
# views.py
@api_view(['GET'])
def new_endpoint(request):
    return Response({"message": "Hello"}, status=200)
```

**Chạy lại test → PASS (GREEN)** ✅

### Bước 3: Refactor (nếu cần)

Cải thiện code mà vẫn giữ test pass.

## 🧪 Test Patterns

### 1. Arrange-Act-Assert

```python
@pytest.mark.django_db
def test_example(api_client, product):
    # ARRANGE: Setup (đã có từ fixtures)
    
    # ACT: Perform action
    response = api_client.get(f"/api/products/{product.id}/")
    
    # ASSERT: Verify result
    assert response.status_code == 200
    assert response.data["name"] == product.name
```

### 2. Test Edge Cases

```python
def test_create_product_with_negative_price(api_client):
    """Test validation: negative price should fail"""
    data = {"name": "Test", "price": -1000, "stock": 10}
    response = api_client.post("/api/products/", data, format="json")
    assert response.status_code == 400

def test_create_product_with_zero_price(api_client):
    """Test edge case: zero price should succeed"""
    data = {"name": "Free", "price": 0, "stock": 10}
    response = api_client.post("/api/products/", data, format="json")
    assert response.status_code == 201
```

### 3. Test Permissions

```python
def test_user_cannot_access_admin_endpoint(authenticated_client):
    """Test that normal user cannot access admin endpoint"""
    response = authenticated_client.post("/api/admin-only/", {...})
    assert response.status_code == 403

def test_admin_can_access_admin_endpoint(admin_client):
    """Test that admin can access admin endpoint"""
    response = admin_client.post("/api/admin-only/", {...})
    assert response.status_code == 201
```

## 📊 Test Coverage

### Chạy coverage report

```bash
# Terminal report
pytest --cov=api --cov-report=term-missing

# HTML report
pytest --cov=api --cov-report=html
# Sau đó mở htmlcov/index.html trong browser
```

### Mục tiêu Coverage

- **Minimum**: 70%
- **Target**: 80%
- **Ideal**: 90%+

## 🔍 Debugging Tests

### Xem print statements

```bash
pytest -s  # Show print statements
```

### Stop at first failure

```bash
pytest -x  # Stop at first failure
```

### Run specific test

```bash
pytest api/tests/test_product_api.py::test_create_product -v
```

### Run tests matching pattern

```bash
pytest -k "product"  # Run all tests with "product" in name
```

## ✅ Test Checklist

Khi viết test mới, đảm bảo:

- [ ] Test có tên mô tả rõ ràng
- [ ] Test độc lập (không phụ thuộc test khác)
- [ ] Sử dụng `@pytest.mark.django_db` cho database operations
- [ ] Test cả happy path và edge cases
- [ ] Test validation errors
- [ ] Test permissions (unauthorized, forbidden)
- [ ] Test với dữ liệu hợp lệ và không hợp lệ
- [ ] Test boundary values

## 🐛 Common Issues

### Issue: Database not found

**Solution**: Đảm bảo có `@pytest.mark.django_db` decorator

```python
@pytest.mark.django_db
def test_example():
    pass
```

### Issue: Fixture not found

**Solution**: Kiểm tra tên fixture trong `conftest.py` hoặc import đúng

### Issue: Authentication not working

**Solution**: Sử dụng `authenticated_client` hoặc `admin_client` fixtures

```python
def test_auth(authenticated_client):
    # authenticated_client đã được setup sẵn
    response = authenticated_client.get("/api/cart/")
```

## 📚 Tài liệu tham khảo

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)

## 🎓 Examples

Xem các file test để học:

- `test_product_api_refactored.py` - Sử dụng fixtures
- `test_product_validation_tdd.py` - TDD pattern cho validation
- `test_product_search_tdd.py` - TDD pattern cho search feature

---

**Happy Testing!** 🧪✨





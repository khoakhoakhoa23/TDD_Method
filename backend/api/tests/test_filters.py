import pytest
from api.filters import ProductFilter
from api.models import Product, Category
from django.test import TestCase
@pytest.fixture
def category(db):
    return Category.objects.create(name="Electronics")


@pytest.fixture
def products(db, category):
    return [
        Product.objects.create(
            name="iPhone 15",
            price=30000000,
            stock=10,
            category=category
        ),
        Product.objects.create(
            name="Samsung Galaxy",
            price=20000000,
            stock=5,
            category=category
        ),
        Product.objects.create(
            name="Nokia Brick",
            price=1000000,
            stock=100,
            category=category
        ),
    ]

@pytest.mark.django_db
def test_product_filter_by_name(products):
    qs = Product.objects.all()
    f = ProductFilter(
        data={"name": "iphone"},
        queryset=qs
    )

    results = f.qs
    assert results.count() == 1
    assert results.first().name == "iPhone 15"

@pytest.mark.django_db
def test_product_filter_min_price(products):
    qs = Product.objects.all()
    f = ProductFilter(
        data={"min_price": 20000000},
        queryset=qs
    )

    results = f.qs
    assert results.count() == 2

@pytest.mark.django_db
def test_product_filter_max_price(products):
    qs = Product.objects.all()
    f = ProductFilter(
        data={"max_price": 5000000},
        queryset=qs
    )

    results = f.qs
    assert results.count() == 1
    assert results.first().name == "Nokia Brick"

@pytest.mark.django_db
def test_product_filter_combined(products, category):
    qs = Product.objects.all()
    f = ProductFilter(
        data={
            "min_price": 1000000,
            "max_price": 25000000,
            "category": category.id,
        },
        queryset=qs
    )

    results = f.qs
    assert results.count() == 2

@pytest.mark.django_db
def test_product_filter_no_params(products):
    qs = Product.objects.all()
    f = ProductFilter(data={}, queryset=qs)

    assert f.qs.count() == 3

@pytest.mark.django_db
def test_product_filter_in_stock(products):
    qs = Product.objects.all()
    f = ProductFilter(
        data={"in_stock": True},
        queryset=qs
    )

    results = f.qs
    assert results.count() == 3

    # Now test out of stock
    products[0].stock = 0
    products[0].save()

    f_out_of_stock = ProductFilter(
        data={"in_stock": False},
        queryset=qs
    )

    results_out_of_stock = f_out_of_stock.qs
    assert results_out_of_stock.count() == 1
    assert results_out_of_stock.first().name == "iPhone 15"
        
@pytest.mark.django_db
def test_filter_in_stock_with_none_returns_queryset(products):
    from api.filters import ProductFilter
    from api.models import Product

    qs = Product.objects.all()
    product_filter = ProductFilter(queryset=qs)

    result = product_filter.filter_in_stock(
        queryset=qs,
        name="in_stock",
        value=None
    )

    assert result.count() == qs.count()
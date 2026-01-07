import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_register_user():
    client = APIClient()

    data = {
        "username": "khoa",
        "password": "anhkhoa123"
    }

    response = client.post("/api/auth/register/", data, format="json")

    assert response.status_code == 201
    assert response.data["username"] == "khoa"

from django.contrib.auth.models import User

@pytest.mark.django_db
def test_login_user_returns_tokens():
    client = APIClient()

    User.objects.create_user(
        username="khoa",
        password="anhkhoa123"
    )

    response = client.post(
        "/api/auth/login/",
        {
            "username": "khoa",
            "password": "anhkhoa123"
        },
        format="json"
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data

@pytest.mark.django_db
def test_me_requires_authentication():
    client = APIClient()

    response = client.get("/api/auth/me/")
    assert response.status_code == 401
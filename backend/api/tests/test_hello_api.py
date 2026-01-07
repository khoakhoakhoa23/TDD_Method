from rest_framework.test import APIClient

def test_hello_api_returns_message():
    client = APIClient()
    response = client.get('/api/hello/')

    assert response.status_code == 200
    assert response.data['message'] == 'Hello from Django'

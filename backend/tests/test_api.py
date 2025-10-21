import pytest
from app.main import app

@pytest.fixture
def client():
    """Create a test client for the app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_hello_world(client):
    """Test the home/index route."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Hello, Clarity AI!" in response.data
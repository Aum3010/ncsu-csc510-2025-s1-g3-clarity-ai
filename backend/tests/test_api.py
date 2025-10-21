import pytest
from app.main import create_app 

@pytest.fixture()
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app

@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()


def test_api_index(client): # Renamed for clarity
    """Test the API's index/health-check route."""
    # Test the NEW endpoint
    response = client.get('/api/') 

    assert response.status_code == 200
    assert b"Welcome to the Clarity AI API!" in response.data
import pytest

# Use fixtures from conftest.py - no need to redefine app and client

def test_api_index(client):
    """Test the API's index/health-check route."""
    # Test the NEW endpoint
    response = client.get('/api/') 

    assert response.status_code == 200
    assert b"Welcome to the Clarity AI API!" in response.data
"""
Health check tests - these run first to verify service is operational.
"""
import pytest
import requests
import os


def get_service_url():
    """Get service URL from environment or default to local."""
    return os.getenv("SERVICE_URL", "http://localhost:8080")


def test_root_endpoint():
    """Test root endpoint returns service info."""
    url = get_service_url()
    response = requests.get(f"{url}/", timeout=10)

    assert response.status_code == 200
    data = response.json()

    assert data["service"] == "Resume Processing Microservice"
    assert data["status"] == "operational"
    assert "version" in data
    assert "endpoints" in data


def test_health_endpoint():
    """Test health check endpoint."""
    url = get_service_url()
    response = requests.get(f"{url}/health", timeout=10)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "resume-processor"
    assert "version" in data
    assert data["openai_configured"] is True  # Should be true in deployment
    assert "modules" in data


def test_health_modules():
    """Test all required modules are ready."""
    url = get_service_url()
    response = requests.get(f"{url}/health", timeout=10)

    data = response.json()
    modules = data["modules"]

    assert modules["structuring"] == "ready"
    assert modules["enhancing"] == "ready"
    assert modules["cover_letter"] == "ready"


def test_unauthorized_access():
    """Test that endpoints require authentication."""
    url = get_service_url()

    # Try structure endpoint without auth
    response = requests.post(
        f"{url}/structure",
        json={"job_text": "test job description" * 20},
        timeout=10
    )

    assert response.status_code == 401
    assert "Authorization" in response.json()["detail"]

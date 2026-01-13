"""
API endpoint tests - test actual functionality with real OpenAI calls.
These tests require OPENAI_API_KEY to be set.
"""
import pytest
import requests
import os
import time


def get_service_url():
    """Get service URL from environment or default to local."""
    return os.getenv("SERVICE_URL", "http://localhost:8080")


def get_api_key():
    """Get API secret key."""
    return os.getenv("API_SECRET_KEY", "dev-secret-key-12345")


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_structure_endpoint(sample_job_text):
    """Test job structuring endpoint."""
    url = get_service_url()
    api_key = get_api_key()

    response = requests.post(
        f"{url}/structure",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "job_text": sample_job_text,
            "source_url": ""
        },
        timeout=60
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "processing_time_seconds" in data

    # Check structured data
    job_data = data["data"]
    assert "job_title" in job_data
    assert "company_name" in job_data
    assert "technical_skills" in job_data
    assert "metadata" in job_data
    assert job_data["metadata"]["language"] in ["en", "fr"]


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_process_endpoint_full_pipeline(sample_job_text, sample_user_json, sample_config_json):
    """Test full pipeline processing."""
    url = get_service_url()
    api_key = get_api_key()

    start_time = time.time()

    response = requests.post(
        f"{url}/process",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "job_text": sample_job_text,
            "user_json": sample_user_json,
            "config_json": sample_config_json
        },
        timeout=120  # Full pipeline can take up to 2 minutes
    )

    elapsed = time.time() - start_time

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "structured_job" in data
    assert "resume" in data
    assert "cover_letter" in data
    assert "metadata" in data

    # Check structured job
    job = data["structured_job"]
    assert "job_title" in job
    assert "company_name" in job

    # Check resume structure
    resume = data["resume"]
    assert "personal" in resume
    assert "contact" in resume
    assert "profile" in resume
    assert "experience" in resume
    assert "skills" in resume
    assert len(resume["experience"]) > 0

    # Check cover letter
    assert data["cover_letter"] is not None
    assert len(data["cover_letter"]) > 100  # Should be substantial

    # Check metadata
    metadata = data["metadata"]
    assert "processing_time_seconds" in metadata
    assert "language" in metadata
    assert "projects_selected" in metadata
    assert metadata["processing_time_seconds"] < 60  # Should be fast

    print(f"\n✓ Full pipeline completed in {elapsed:.2f}s")
    print(f"  Job: {job['job_title']} at {job['company_name']}")
    print(f"  Projects selected: {len(metadata['projects_selected'])}")
    print(f"  Language: {metadata['language']}")
    print(f"  ATS Score: {metadata.get('average_ats_score', 'N/A')}")


def test_invalid_request_missing_auth():
    """Test request without authorization."""
    url = get_service_url()

    response = requests.post(
        f"{url}/process",
        json={
            "job_text": "test",
            "user_json": {},
            "config_json": {}
        },
        timeout=10
    )

    assert response.status_code == 401


def test_invalid_request_short_job_text(sample_user_json, sample_config_json):
    """Test request with job text that's too short."""
    url = get_service_url()
    api_key = get_api_key()

    response = requests.post(
        f"{url}/process",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "job_text": "short",  # Too short
            "user_json": sample_user_json,
            "config_json": sample_config_json
        },
        timeout=10
    )

    assert response.status_code == 400
    assert "at least 50 characters" in response.json()["detail"]


def test_invalid_request_missing_user_json(sample_job_text, sample_config_json):
    """Test request without user_json."""
    url = get_service_url()
    api_key = get_api_key()

    response = requests.post(
        f"{url}/process",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "job_text": sample_job_text,
            "config_json": sample_config_json
        },
        timeout=10
    )

    assert response.status_code == 422  # Validation error

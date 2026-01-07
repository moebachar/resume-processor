"""
Pytest configuration and fixtures for testing.
"""
import pytest
import os
import json
from pathlib import Path


@pytest.fixture
def sample_job_text():
    """Sample job description for testing."""
    return """
    Senior Software Engineer - AI/ML

    Tech Startup in Paris

    We are seeking a talented Senior Software Engineer with expertise in AI and Machine Learning.

    Requirements:
    - 2+ years of experience in software engineering
    - Strong proficiency in Python, FastAPI, and Docker
    - Experience with ML frameworks (TensorFlow, PyTorch)
    - Knowledge of cloud platforms (Azure, AWS, GCP)

    Responsibilities:
    - Design and develop scalable AI-powered applications
    - Build and maintain microservices architecture
    - Write clean, maintainable code
    """


@pytest.fixture
def sample_user_json():
    """Sample user data for testing."""
    return {
        "personal": {
            "name": "Test User",
            "title": "Software Engineer",
            "degree": "Master's in Computer Science",
            "gender": "male"
        },
        "contact": {
            "email": "test@example.com",
            "phone": "+1234567890",
            "linkedin": "linkedin.com/in/testuser"
        },
        "education": [
            {
                "degree": {"en": "Master's in Computer Science", "fr": "Master en Informatique"},
                "institution": "Test University",
                "location": {"en": "Paris, France", "fr": "Paris, France"},
                "start": "2018-09",
                "end": "2020-06",
                "description": {"en": "Focus on AI and ML", "fr": "Spécialisation IA et ML"}
            }
        ],
        "projects_database": {
            "Project A": {
                "company": "Tech Corp",
                "start_date": "2020-01",
                "end_date": "2022-12",
                "location": {"en": "Paris, France", "fr": "Paris, France"},
                "contexte": "AI-powered application",
                "technologies": ["Python", "FastAPI", "Docker", "TensorFlow"],
                "realisations": [
                    "Built scalable microservices architecture serving 1M+ users",
                    "Implemented ML models for personalized recommendations",
                    "Reduced API latency by 60% through optimization"
                ]
            },
            "Project B": {
                "company": "Startup Inc",
                "start_date": "2019-06",
                "end_date": "2020-12",
                "location": {"en": "Remote", "fr": "À distance"},
                "contexte": "Microservices architecture",
                "technologies": ["Python", "Kubernetes", "PostgreSQL"],
                "realisations": [
                    "Designed and deployed Kubernetes-based infrastructure",
                    "Implemented CI/CD pipelines reducing deployment time by 80%",
                    "Maintained 99.9% uptime for critical services"
                ]
            },
            "Project C": {
                "company": "Data Co",
                "start_date": "2018-01",
                "end_date": "2019-05",
                "location": {"en": "Lyon, France", "fr": "Lyon, France"},
                "contexte": "Data pipeline",
                "technologies": ["Python", "Pandas", "Airflow"],
                "realisations": [
                    "Built ETL pipelines processing 10TB+ data daily",
                    "Automated data quality checks reducing errors by 95%"
                ]
            }
        },
        "skills_database": {
            "skills": {
                "Python": {"category": "programming", "proficiency": "expert"},
                "FastAPI": {"category": "framework", "proficiency": "advanced"},
                "Docker": {"category": "devops", "proficiency": "advanced"},
                "TensorFlow": {"category": "ml", "proficiency": "intermediate"},
                "PostgreSQL": {"category": "database", "proficiency": "intermediate"}
            },
            "essential_skills": ["Python", "FastAPI", "Docker"]
        },
        "languages": [
            {
                "language": {"en": "English", "fr": "Anglais"},
                "proficiency": {"en": "Fluent", "fr": "Courant"}
            },
            {
                "language": {"en": "French", "fr": "Français"},
                "proficiency": {"en": "Native", "fr": "Langue maternelle"}
            }
        ],
        "certifications": []
    }


@pytest.fixture
def sample_config_json():
    """Sample config data for testing."""
    return {
        "openai": {
            "default_model": "gpt-4o-mini",
            "temperature": 0.7
        },
        "structuring": {
            "model": "gpt-4o-mini"
        },
        "enhancing": {
            "coordinator": {
                "model": "gpt-4o-mini"
            },
            "bullet_coordinator": {
                "model": "gpt-4o-mini",
                "temperature": 0.6
            },
            "bullet_adaptation": {
                "bullets_per_experience": 4,
                "max_bullet_length": 150
            },
            "profile_generation": {
                "model": "gpt-4o-mini"
            },
            "skills_generation": {
                "target_technical_skills": 25,
                "num_soft_skills": 5
            },
            "cover_letter": {
                "model": "gpt-4o-mini"
            }
        }
    }


@pytest.fixture
def api_key():
    """Get API key from environment."""
    return os.getenv("API_SECRET_KEY", "dev-secret-key-12345")


@pytest.fixture
def openai_api_key():
    """Get OpenAI API key from environment."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set")
    return key

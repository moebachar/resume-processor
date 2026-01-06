"""
Job Description Schema for Resume Adaptation

This module provides utility functions for job data validation and initialization.
The actual schema is defined in main.py's build_json_schema() function.
"""


def get_empty_job() -> dict:
    """
    Returns an empty job structure with all fields initialized.

    Returns:
        dict: Empty job structure following the schema
    """
    return {
        "job_title": "",
        "company_name": "",
        "location": {
            "city": "",
            "remote_policy": "not_specified"
        },
        "technical_skills": [],
        "soft_skills": [],
        "experience_required": {
            "years": "",
            "relevant_domains": []
        },
        "education_required": {
            "level": "",
            "fields": []
        },
        "languages": [],
        "responsibilities": [],
        "keywords": [],
        "company_values": [],
        "action_verbs": [],
        "technical_priorities": {
            "must_have": [],
            "preferred": []
        },
        "domain_terminology": [],
        "metadata": {
            "source_url": "",
            "extraction_date": "",
            "language": ""
        }
    }


def validate_job(job: dict) -> tuple[bool, list[str]]:
    """
    Validate that a job dict follows the required schema.

    Args:
        job: Dictionary to validate

    Returns:
        tuple: (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    required_fields = [
        "job_title",
        "company_name",
        "technical_skills",
        "soft_skills",
        "responsibilities",
        "keywords",
        "metadata"
    ]

    for field in required_fields:
        if field not in job:
            errors.append(f"Missing required field: {field}")
        elif field in ["technical_skills", "soft_skills", "responsibilities", "keywords"]:
            if not isinstance(job[field], list):
                errors.append(f"Field '{field}' must be a list")

    # Check metadata
    if "metadata" in job:
        if "extraction_date" not in job["metadata"]:
            errors.append("Missing required field: metadata.extraction_date")

    return (len(errors) == 0, errors)

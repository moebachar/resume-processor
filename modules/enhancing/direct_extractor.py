"""
Direct Experience Extractor

Extracts experience data directly from project without AI enhancement.
Used when content_strategy="direct" for an experience.
"""

from typing import Dict, Any, List


def extract_lang(value: Any, lang: str) -> str:
    """Extract language-specific string from object or return as-is if string"""
    if isinstance(value, dict) and lang in value:
        return value[lang]
    elif isinstance(value, dict):
        return next(iter(value.values()), "")
    return value if isinstance(value, str) else ""


def extract_direct_experience(
    project_name: str,
    project_data: Dict[str, Any],
    role_title: str,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Extract experience data directly from project without AI enhancement.

    Args:
        project_name: Name of the project
        project_data: Project data from projects_database
        role_title: Role title (from coordinator - either direct or enhanced)
        language: Language code (en/fr)

    Returns:
        Direct experience dict with original content (no enhancement)
    """
    # Extract realisations (bullet points) directly
    realisations = project_data.get("realisations", [])

    # Handle different formats of realisations
    if isinstance(realisations, dict):
        # Language-specific format: {"en": [...], "fr": [...]}
        bullets = realisations.get(language, realisations.get("en", []))
    elif isinstance(realisations, list):
        # Direct list format
        bullets = realisations
    else:
        bullets = []

    # Ensure bullets are strings
    if bullets and isinstance(bullets[0], dict):
        # If bullets are objects with text field
        bullets = [b.get("text", str(b)) for b in bullets]

    return {
        "project_name": project_name,
        "role": role_title,
        "company": project_data.get("company", ""),
        "location": extract_lang(project_data.get("location", {}), language),
        "start_date": project_data.get("start_date", ""),
        "end_date": project_data.get("end_date", ""),
        "bullets": [
            {"text": b, "ats_score": 0.0, "keywords_used": []}
            for b in bullets
        ],
        "context": project_data.get("contexte", ""),
        "average_ats_score": 0.0,  # No ATS optimization for direct
        "keywords_used": [],  # No keyword tracking
        "is_direct": True  # Flag to identify direct experiences
    }


def extract_direct_role(
    project_data: Dict[str, Any],
    language: str = "en"
) -> str:
    """
    Extract the best role title directly from project's available roles (metiers).

    Args:
        project_data: Project data from projects_database
        language: Language code (en/fr)

    Returns:
        Best matching role title from project
    """
    metiers = project_data.get("metiers", [])

    if not metiers:
        # Fallback to project name or generic title
        return project_data.get("name", "Software Engineer")

    # Return the first role (usually the primary/best one)
    first_role = metiers[0]

    if isinstance(first_role, dict):
        return extract_lang(first_role, language)

    return str(first_role)


def get_available_roles(
    project_data: Dict[str, Any],
    language: str = "en"
) -> List[str]:
    """
    Get all available role titles from a project.

    Args:
        project_data: Project data from projects_database
        language: Language code (en/fr)

    Returns:
        List of available role titles
    """
    metiers = project_data.get("metiers", [])

    roles = []
    for metier in metiers:
        if isinstance(metier, dict):
            roles.append(extract_lang(metier, language))
        else:
            roles.append(str(metier))

    return roles if roles else ["Software Engineer"]

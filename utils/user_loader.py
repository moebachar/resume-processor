"""
User Data Loader

Centralized utility to load user-specific information from user.json.
This makes the system user-agnostic and easy to customize.
"""

import json
import importlib
from pathlib import Path
from typing import Dict, Any, Optional


# Cache for user data (loaded once)
_user_data_cache: Optional[Dict[str, Any]] = None


def get_user_file_path() -> Path:
    """
    Get the path to user.json file.

    Returns:
        Path: Absolute path to user.json
    """
    # user.json is in project root
    project_root = Path(__file__).parent.parent
    return project_root / "user.json"


def load_user_data(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load user data from user.json file.

    Args:
        force_reload: Force reload from file even if cached

    Returns:
        Dict: User data dictionary (empty dict if file not found in microservice mode)

    Raises:
        json.JSONDecodeError: If user.json is invalid
    """
    global _user_data_cache

    # Return cached data if available and not forcing reload
    if _user_data_cache is not None and not force_reload:
        return _user_data_cache

    user_file = get_user_file_path()

    if not user_file.exists():
        # In microservice mode, user data is passed via API, not from file
        _user_data_cache = {}
        return _user_data_cache

    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            _user_data_cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Gracefully handle missing or invalid file in microservice mode
        _user_data_cache = {}

    return _user_data_cache


def get_user_value(key_path: str, default: Any = None) -> Any:
    """
    Get a specific value from user data using dot notation.

    Args:
        key_path: Dot-separated path to the value (e.g., 'personal.name', 'contact.email')
        default: Default value if key not found

    Returns:
        Any: The value at key_path, or default if not found

    Examples:
        >>> get_user_value('personal.name')
        'Mohamed BACHAR'
        >>> get_user_value('contact.email')
        'm.bachar.fr@gmail.com'
        >>> get_user_value('personal.gender')
        'male'
    """
    try:
        user_data = load_user_data()
        keys = key_path.split('.')

        value = user_data
        for key in keys:
            value = value[key]

        return value
    except (KeyError, TypeError):
        return default


def get_user_name() -> str:
    """Get user's full name."""
    return get_user_value('personal.name', '')


def get_user_gender() -> str:
    """
    Get user's gender.

    Returns:
        str: 'male' or 'female'
    """
    return get_user_value('personal.gender', 'male')


def get_user_degree() -> str:
    """Get user's degree/education title."""
    return get_user_value('personal.degree', 'Engineer')


def get_user_title() -> str:
    """Get user's professional title."""
    return get_user_value('personal.title', '')


def get_user_contact() -> Dict[str, str]:
    """
    Get user's contact information.

    Returns:
        Dict with keys: email, phone, location, linkedin, github, website
    """
    return get_user_value('contact', {})


def get_user_email() -> str:
    """Get user's email address."""
    return get_user_value('contact.email', '')


def get_user_phone() -> str:
    """Get user's phone number."""
    return get_user_value('contact.phone', '')


def get_user_location() -> str:
    """Get user's location."""
    return get_user_value('contact.location', '')


def load_projects_database() -> Dict[str, Any]:
    """
    Load user's projects database from user.json.

    Returns:
        Dict: Projects database

    Raises:
        KeyError: If projects_database not found in user.json
    """
    user_data = load_user_data()

    # Try new format (embedded in user.json)
    if 'projects_database' in user_data:
        return user_data['projects_database']

    # Fallback: try old format (external .py file) for backward compatibility
    if 'databases' in user_data and 'projects' in user_data['databases']:
        db_file = user_data['databases']['projects']
        module_name = db_file.replace('.py', '')
        try:
            module = importlib.import_module(module_name)
            return getattr(module, 'PROJECTS_DATABASE', {})
        except ImportError as e:
            raise ImportError(
                f"Could not load projects database from {db_file}: {e}\n"
                f"Please add projects_database to user.json or ensure {db_file} exists."
            )

    raise KeyError(
        "projects_database not found in user.json.\n"
        "Please add a 'projects_database' section to user.json."
    )


def load_skills_database() -> Dict[str, Any]:
    """
    Load user's skills database from user.json.

    Returns:
        Dict: Skills database with 'skills' and 'essential_skills' keys

    Raises:
        KeyError: If skills_database not found in user.json
    """
    user_data = load_user_data()

    # Try new format (embedded in user.json)
    if 'skills_database' in user_data:
        return user_data['skills_database']

    # Fallback: try old format (external .py file) for backward compatibility
    if 'databases' in user_data and 'skills' in user_data['databases']:
        db_file = user_data['databases']['skills']
        module_name = db_file.replace('.py', '')
        try:
            module = importlib.import_module(module_name)
            # Return in new format
            return {
                'skills': getattr(module, 'SKILLS', {}),
                'essential_skills': getattr(module, 'ECENTIAL_SKILLS', [])
            }
        except ImportError as e:
            raise ImportError(
                f"Could not load skills database from {db_file}: {e}\n"
                f"Please add skills_database to user.json or ensure {db_file} exists."
            )

    raise KeyError(
        "skills_database not found in user.json.\n"
        "Please add a 'skills_database' section to user.json."
    )


def get_skills() -> Dict[str, Any]:
    """
    Get user's skills dictionary.

    Returns:
        Dict: Skills with category and order information
    """
    skills_db = load_skills_database()
    return skills_db.get('skills', {})


def get_essential_skills() -> list:
    """
    Get user's essential skills list.

    Returns:
        List: Essential skills that should always be included
    """
    skills_db = load_skills_database()
    return skills_db.get('essential_skills', [])


def get_user_languages() -> list:
    """
    Get user's spoken languages.

    Returns:
        List of dicts with 'language' and 'level' keys
    """
    return get_user_value('languages', [])


def get_user_education() -> list:
    """
    Get user's education history.

    Returns:
        List of education entries
    """
    return get_user_value('education', [])


def get_user_certifications() -> list:
    """
    Get user's certifications.

    Returns:
        List of certification entries
    """
    return get_user_value('certifications', [])


def get_user_preferences() -> Dict[str, Any]:
    """
    Get user's preferences.

    Returns:
        Dict with user preferences
    """
    return get_user_value('preferences', {})


def get_profile_photo_path() -> str:
    """Get path to user's profile photo."""
    return get_user_value('preferences.profile_photo', '')


# Backward compatibility aliases (for gradual migration)
GENDER = None  # Will be loaded on first access
USER_NAME = None
USER_DEGREE = None
CONTACT_INFO = None


def _load_legacy_values():
    """Load legacy values from user.json for backward compatibility."""
    global GENDER, USER_NAME, USER_DEGREE, CONTACT_INFO

    if GENDER is None:
        GENDER = get_user_gender()
    if USER_NAME is None:
        USER_NAME = get_user_name()
    if USER_DEGREE is None:
        USER_DEGREE = get_user_degree()
    if CONTACT_INFO is None:
        CONTACT_INFO = get_user_contact()


# Auto-load on import for backward compatibility
try:
    _load_legacy_values()
except Exception:
    # If user.json doesn't exist yet, set defaults
    GENDER = "male"
    USER_NAME = ""
    USER_DEGREE = "Engineer"
    CONTACT_INFO = {}

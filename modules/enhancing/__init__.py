"""
Enhancing module for resume enhancement.

Provides async implementations for parallel execution and improved performance.
Supports dynamic experience configuration with direct/enhanced strategies.
"""

from .coordinator import coordinate_enhancement, coordinate_experiences
from .bullet_coordinator import generate_bullets_with_coordinator
from .profile_generator import generate_profile_description
from .skills_generator import generate_skills_list
from .direct_extractor import extract_direct_experience, extract_direct_role, get_available_roles

__all__ = [
    'coordinate_enhancement',  # Legacy: auto-select 3 projects
    'coordinate_experiences',  # New: dynamic experience configuration
    'generate_bullets_with_coordinator',
    'generate_profile_description',
    'generate_skills_list',
    'extract_direct_experience',
    'extract_direct_role',
    'get_available_roles'
]

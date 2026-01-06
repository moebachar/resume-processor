"""
Skills Cleaner

Filters out verbs, actions, and non-technical content from skills lists.
Keeps only real technologies, tools, and frameworks.
"""

import re
from typing import List


# Common French/English action verbs that appear in "skills" but aren't skills
ACTION_VERBS = [
    # French verbs
    "développer", "créer", "concevoir", "implémenter", "mettre en place",
    "déployer", "gérer", "analyser", "optimiser", "améliorer", "construire",
    "élaborer", "réaliser", "effectuer", "assurer", "garantir", "maintenir",
    "suivre", "utiliser", "maîtriser", "collaborer", "participer", "contribuer",
    "rédiger", "documenter", "former", "encadrer", "piloter", "coordonner",

    # English verbs
    "develop", "create", "design", "implement", "deploy", "build", "manage",
    "analyze", "optimize", "improve", "maintain", "ensure", "guarantee",
    "follow", "use", "master", "collaborate", "participate", "contribute",
    "write", "document", "train", "lead", "coordinate", "establish"
]

# Non-skill phrases (objectives, soft skills, etc.)
NON_SKILL_PATTERNS = [
    # French patterns
    r"^capacité (à|de|d')",
    r"^compétence (en|pour|dans)",
    r"^expérience (avec|en|dans)",
    r"^connaissance (de|des|en)",
    r"^maîtrise (de|des|du)",
    r"^esprit d'équipe",
    r"^sens (de|du|des)",
    r"^autonomie",
    r"^rigueur",
    r"^communication",
    r"^organisation",
    r"^gestion (de|du|des) (projet|équipe|temps)",
    r"^travail (d'équipe|en équipe)",
    r"^résolution de problèmes",

    # English patterns
    r"^ability to",
    r"^experience with",
    r"^knowledge of",
    r"^understanding of",
    r"^teamwork",
    r"^communication skills",
    r"^problem solving",
    r"^time management",
    r"^project management",

    # Generic patterns
    r"^\d+\s*(ans?|années?|years?)",  # "2 ans", "3 years"
    r"^niveau\s+",  # "niveau avancé"
    r"^bon(ne)?\s+",  # "bonne connaissance"
    r"^très\s+",  # "très autonome"
    r"^level\s+",  # "level advanced"
    r"^strong\s+",  # "strong knowledge"
    r"^good\s+",  # "good understanding"
]

# Minimum length for valid skills
MIN_SKILL_LENGTH = 2
MAX_SKILL_LENGTH = 50


def is_action_verb(text: str) -> bool:
    """
    Check if text starts with an action verb.

    Args:
        text: Text to check

    Returns:
        bool: True if starts with action verb
    """
    text_lower = text.lower().strip()

    # Check if starts with any action verb
    for verb in ACTION_VERBS:
        if text_lower.startswith(verb):
            # Make sure it's a verb usage, not part of a technology name
            # e.g., "Docker" shouldn't match even if it contains "doc"
            if len(text_lower) == len(verb) or text_lower[len(verb)] in [' ', ',', '.', ';']:
                return True

    return False


def is_non_skill_phrase(text: str) -> bool:
    """
    Check if text is a non-skill phrase (soft skill, objective, etc.).

    Args:
        text: Text to check

    Returns:
        bool: True if non-skill phrase
    """
    text_lower = text.lower().strip()

    # Check against patterns
    for pattern in NON_SKILL_PATTERNS:
        if re.match(pattern, text_lower, re.IGNORECASE):
            return True

    return False


def is_too_long_or_short(text: str) -> bool:
    """
    Check if text is too long or short to be a valid skill.

    Args:
        text: Text to check

    Returns:
        bool: True if invalid length
    """
    return len(text) < MIN_SKILL_LENGTH or len(text) > MAX_SKILL_LENGTH


def is_sentence_or_phrase(text: str) -> bool:
    """
    Check if text is a full sentence or long phrase (not a skill name).

    Args:
        text: Text to check

    Returns:
        bool: True if sentence/phrase
    """
    # Count words
    words = text.split()

    # More than 6 words = probably a phrase/sentence
    if len(words) > 6:
        return True

    # Contains verbs in context (verb + object)
    # e.g., "développer des modèles ML" = sentence
    if any(verb in text.lower() for verb in ["développer", "créer", "mettre", "construire"]):
        if len(words) >= 3:  # verb + article + noun = sentence
            return True

    return False


def looks_like_technology(text: str) -> bool:
    """
    Check if text looks like a technology/tool name.

    Technologies typically:
    - Are proper nouns (capitalized)
    - Are acronyms (all caps)
    - Are short (1-3 words)
    - Don't contain verbs

    Args:
        text: Text to check

    Returns:
        bool: True if looks like technology
    """
    text_stripped = text.strip()
    words = text_stripped.split()

    # Single word = likely technology
    if len(words) == 1:
        return True

    # Acronym (all caps, 2-8 chars)
    if text_stripped.isupper() and 2 <= len(text_stripped) <= 8:
        return True

    # Capitalized (proper noun) and short
    if text_stripped[0].isupper() and len(words) <= 3:
        return True

    # Common technology patterns
    if any(pattern in text_stripped for pattern in [
        "SQL", "DB", "API", ".js", ".py", "ML", "AI", "CI/CD"
    ]):
        return True

    return False


def clean_skill(skill: str) -> str:
    """
    Clean a single skill string.

    Args:
        skill: Raw skill string

    Returns:
        str: Cleaned skill string
    """
    # Remove extra whitespace
    skill = " ".join(skill.split())

    # Remove trailing punctuation
    skill = skill.rstrip('.,;:')

    return skill


def is_valid_skill(skill: str) -> bool:
    """
    Check if a skill string is valid (real technology/tool).

    Args:
        skill: Skill to validate

    Returns:
        bool: True if valid skill
    """
    skill_clean = clean_skill(skill)

    # Empty or too short/long
    if is_too_long_or_short(skill_clean):
        return False

    # Action verb
    if is_action_verb(skill_clean):
        return False

    # Non-skill phrase (soft skill, objective, etc.)
    if is_non_skill_phrase(skill_clean):
        return False

    # Full sentence or long phrase
    if is_sentence_or_phrase(skill_clean):
        return False

    # Looks like technology = keep
    if looks_like_technology(skill_clean):
        return True

    # If not clearly a technology, check if it's lowercase and multi-word
    # (might be a sentence fragment)
    words = skill_clean.split()
    if len(words) >= 3 and skill_clean[0].islower():
        return False  # Probably a phrase

    # Default: keep it (benefit of doubt)
    return True


def filter_skills(skills: List[str], verbose: bool = False) -> List[str]:
    """
    Filter a list of skills, keeping only valid technologies/tools.

    Args:
        skills: List of raw skill strings
        verbose: Print filtering info

    Returns:
        List[str]: Filtered skills list
    """
    if not skills:
        return []

    filtered = []
    removed = []

    for skill in skills:
        skill_clean = clean_skill(skill)

        if is_valid_skill(skill_clean):
            filtered.append(skill_clean)
        else:
            removed.append(skill_clean)

    if verbose and removed:
        print(f"\n  Filtered out {len(removed)} non-skills:")
        for removed_skill in removed[:10]:  # Show first 10
            print(f"    - {removed_skill}")
        if len(removed) > 10:
            print(f"    ... and {len(removed) - 10} more")

    return filtered


# Test cases
if __name__ == "__main__":
    test_skills = [
        # Valid skills
        "Python",
        "TensorFlow",
        "Docker",
        "PostgreSQL",
        "AWS",
        "CI/CD",
        "Machine Learning",
        "React.js",

        # Invalid (verbs/actions)
        "développer des modèles ML",
        "créer des pipelines de données",
        "mettre en place des architectures",
        "utiliser Docker",

        # Invalid (soft skills)
        "esprit d'équipe",
        "capacité à communiquer",
        "autonomie",
        "rigueur",

        # Invalid (phrases)
        "2 ans d'expérience en Python",
        "bonne connaissance de Docker",
        "maîtrise des frameworks ML",
    ]

    print("Testing skill filtering:")
    print("=" * 60)

    for skill in test_skills:
        is_valid = is_valid_skill(skill)
        status = "✓ KEEP" if is_valid else "✗ REMOVE"
        print(f"{status:12} | {skill}")

    print("\n" + "=" * 60)
    filtered = filter_skills(test_skills, verbose=True)
    print(f"\nFinal: {len(filtered)}/{len(test_skills)} skills kept")
    print(f"Skills: {filtered}")

"""
Gender Text Processor

Removes French gender brackets based on user gender.
Converts: "consultant(e)" → "consultant" (male) or "consultante" (female)
"""

import re
from typing import List, Dict, Any


def remove_gender_brackets(text: str, gender: str = "male") -> str:
    """
    Remove French gender brackets based on user gender.

    Examples:
        Male:
            "consultant(e)" → "consultant"
            "organisé(e)" → "organisé"
            "rigoureux(se)" → "rigoureux"
            "développeur(euse)" → "développeur"
            "autonome (H/F)" → "autonome"

        Female:
            "consultant(e)" → "consultante"
            "organisé(e)" → "organisée"
            "rigoureux(se)" → "rigoureuse"
            "développeur(euse)" → "développeuse"
            "autonome (H/F)" → "autonome"

    Args:
        text: Text with potential gender brackets
        gender: "male" or "female"

    Returns:
        str: Cleaned text
    """
    if not text:
        return text

    # Pattern 1: word(e) → word or worde
    # Examples: consultant(e), organisé(e), passionné(e)
    if gender == "male":
        text = re.sub(r'\(e\)', '', text, flags=re.IGNORECASE)
    else:
        text = re.sub(r'\(e\)', 'e', text, flags=re.IGNORECASE)

    # Pattern 2: word(se) → word or wordse
    # Examples: rigoureux(se), curieux(se), sérieux(se)
    if gender == "male":
        text = re.sub(r'x\(se\)', 'x', text, flags=re.IGNORECASE)
    else:
        text = re.sub(r'x\(se\)', 'se', text, flags=re.IGNORECASE)

    # Pattern 3: word(euse) → word or wordeuse
    # Examples: développeur(euse), testeur(euse)
    if gender == "male":
        text = re.sub(r'r\(euse\)', 'r', text, flags=re.IGNORECASE)
    else:
        text = re.sub(r'r\(euse\)', 'reuse', text, flags=re.IGNORECASE)

    # Pattern 4: word(trice) → word or wordtrice
    # Examples: directeur(trice), acteur(trice)
    if gender == "male":
        text = re.sub(r'eur\(trice\)', 'eur', text, flags=re.IGNORECASE)
    else:
        text = re.sub(r'eur\(trice\)', 'rice', text, flags=re.IGNORECASE)

    # Pattern 5: (H/F), (F/H), h/f markers - always remove
    text = re.sub(r'\s*\([HF]/[HF]\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*[HF]/[HF]\s*', ' ', text, flags=re.IGNORECASE)

    # Pattern 6: word(ne) → word or wordne
    # Examples: ancien(ne), bon(ne)
    if gender == "male":
        text = re.sub(r'\(ne\)', '', text, flags=re.IGNORECASE)
    else:
        text = re.sub(r'\(ne\)', 'ne', text, flags=re.IGNORECASE)

    # Pattern 7: word(le) → word or wordle
    # Examples: professionnel(le), relationnel(le)
    if gender == "male":
        text = re.sub(r'\(le\)', '', text, flags=re.IGNORECASE)
    else:
        text = re.sub(r'\(le\)', 'le', text, flags=re.IGNORECASE)

    # Pattern 8: word(ve) → word or wordve
    # Examples: attentif(ve), créatif(ve)
    if gender == "male":
        text = re.sub(r'f\(ve\)', 'f', text, flags=re.IGNORECASE)
    else:
        text = re.sub(r'f\(ve\)', 've', text, flags=re.IGNORECASE)

    # Clean up any double spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def clean_bullet_points(bullets: List[Dict[str, Any]], gender: str = "male") -> List[Dict[str, Any]]:
    """
    Clean gender brackets from bullet point texts.

    Args:
        bullets: List of bullet point dicts with 'text' field
        gender: "male" or "female"

    Returns:
        List[Dict]: Cleaned bullet points
    """
    cleaned_bullets = []

    for bullet in bullets:
        cleaned_bullet = bullet.copy()
        if 'text' in cleaned_bullet:
            cleaned_bullet['text'] = remove_gender_brackets(cleaned_bullet['text'], gender)
        cleaned_bullets.append(cleaned_bullet)

    return cleaned_bullets


def clean_profile_description(profile: str, gender: str = "male") -> str:
    """
    Clean gender brackets from profile description.

    Args:
        profile: Profile description text
        gender: "male" or "female"

    Returns:
        str: Cleaned profile
    """
    return remove_gender_brackets(profile, gender)


def clean_enhanced_experiences(experiences: List[Dict[str, Any]], gender: str = "male") -> List[Dict[str, Any]]:
    """
    Clean gender brackets from all enhanced experiences.

    Args:
        experiences: List of enhanced experience dicts
        gender: "male" or "female"

    Returns:
        List[Dict]: Cleaned experiences
    """
    cleaned_experiences = []

    for experience in experiences:
        cleaned_exp = experience.copy()

        # Clean bullets
        if 'bullets' in cleaned_exp:
            cleaned_exp['bullets'] = clean_bullet_points(cleaned_exp['bullets'], gender)

        # Clean role if present
        if 'role' in cleaned_exp:
            cleaned_exp['role'] = remove_gender_brackets(cleaned_exp['role'], gender)

        # Clean title if present
        if 'title' in cleaned_exp:
            cleaned_exp['title'] = remove_gender_brackets(cleaned_exp['title'], gender)

        cleaned_experiences.append(cleaned_exp)

    return cleaned_experiences


# Test cases for verification
if __name__ == "__main__":
    test_cases_male = [
        "consultant(e) en data science",
        "développeur(euse) Python",
        "rigoureux(se) et organisé(e)",
        "Ingénieur(e) Machine Learning (H/F)",
        "professionnel(le) et autonome",
        "attentif(ve) aux détails",
        "bon(ne) communicant(e)"
    ]

    print("Testing MALE gender:")
    print("=" * 60)
    for test in test_cases_male:
        result = remove_gender_brackets(test, "male")
        print(f"{test:50} → {result}")

    print("\n\nTesting FEMALE gender:")
    print("=" * 60)
    for test in test_cases_male:
        result = remove_gender_brackets(test, "female")
        print(f"{test:50} → {result}")

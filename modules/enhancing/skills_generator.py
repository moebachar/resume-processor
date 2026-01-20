"""
Skills List Generation Module (Async Version)

Simple, minimal approach:
1. Essential skills (mandatory)
2. Validated skills from bullets (mandatory)
3. Job-required skills from user DB (if needed to reach target)
4. Complementary skills from user DB (if needed to reach target)
5. Soft skills (mandatory, at the end)
"""

from typing import List, Dict, Any, Set, Union
import numpy as np
import sys
from pathlib import Path

# Import skills cleaner
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.skills_cleaner import filter_skills


def normalize_skill_name(skill: str) -> str:
    """
    Normalize skill name for matching (lowercase, remove special chars).

    Args:
        skill: Skill name to normalize

    Returns:
        str: Normalized skill name
    """
    import re
    normalized = skill.lower()
    normalized = re.sub(r'[/\-\.\s]+', '', normalized)
    return normalized


def fuzzy_match_skills(skill: str, skill_list: List[str]) -> bool:
    """
    Check if a skill matches any skill in the list (fuzzy, case-insensitive).

    Args:
        skill: Skill to check
        skill_list: List of skills to match against

    Returns:
        bool: True if skill matches any in list
    """
    skill_norm = normalize_skill_name(skill)

    for list_skill in skill_list:
        list_skill_norm = normalize_skill_name(list_skill)

        # Exact match after normalization
        if skill_norm == list_skill_norm:
            return True

        # Substring match (e.g., "Postgres" in "PostgreSQL")
        if skill_norm in list_skill_norm or list_skill_norm in skill_norm:
            return True

    return False


def extract_validated_skills(enhanced_experiences: List[Dict[str, Any]]) -> List[str]:
    """
    Extract all skills that were actually used in bullet points.

    For enhanced experiences: extracts keywords_used from bullets
    For direct experiences: extracts keywords_used (if any) from bullets

    Args:
        enhanced_experiences: List of adapted experiences with bullets
            (can include both enhanced and direct experiences)

    Returns:
        List[str]: Unique validated skills
    """
    validated_skills = set()

    for experience in enhanced_experiences:
        # Check if this is a direct or enhanced experience
        is_direct = experience.get("is_direct", False)

        for bullet in experience.get("bullets", []):
            # For both types, extract keywords_used if present
            keywords = bullet.get("keywords_used", [])
            validated_skills.update(keywords)

        # For direct experiences, also include any explicitly tracked keywords
        if is_direct:
            direct_keywords = experience.get("keywords_used", [])
            validated_skills.update(direct_keywords)

    return list(validated_skills)


def get_job_required_skills(job_data: Dict[str, Any], user_skills_db: List[str]) -> List[str]:
    """
    Get job-required skills that exist in user's database.

    Priority: must_have > preferred > other technical skills

    Args:
        job_data: Structured job JSON
        user_skills_db: All skills from user's database

    Returns:
        List[str]: Job-required skills (prioritized)
    """
    must_have = job_data.get("technical_priorities", {}).get("must_have", [])
    preferred = job_data.get("technical_priorities", {}).get("preferred", [])
    all_job_skills = job_data.get("technical_skills", [])

    job_skills = []

    # Priority 1: Must-have skills
    for job_skill in must_have:
        for db_skill in user_skills_db:
            if fuzzy_match_skills(job_skill, [db_skill]) and db_skill not in job_skills:
                job_skills.append(db_skill)
                break

    # Priority 2: Preferred skills
    for job_skill in preferred:
        for db_skill in user_skills_db:
            if fuzzy_match_skills(job_skill, [db_skill]) and db_skill not in job_skills:
                job_skills.append(db_skill)
                break

    # Priority 3: Other technical skills
    for job_skill in all_job_skills:
        if job_skill in must_have or job_skill in preferred:
            continue  # Already added
        for db_skill in user_skills_db:
            if fuzzy_match_skills(job_skill, [db_skill]) and db_skill not in job_skills:
                job_skills.append(db_skill)
                break

    return job_skills


async def get_complementary_skills(
    already_selected: List[str],
    user_skills_db: List[str],
    client,
    count: int
) -> List[str]:
    """
    Find complementary skills from DB using semantic similarity (ASYNC).

    Finds skills similar to already selected ones but not yet included.

    Args:
        already_selected: Skills already in the list
        user_skills_db: All skills from user's database
        client: AsyncOpenAI client for embeddings
        count: Number of complementary skills to return

    Returns:
        List[str]: Complementary skills
    """
    if count <= 0 or not already_selected:
        return []

    # Get candidate skills (in DB, not yet selected)
    candidates = [
        skill for skill in user_skills_db
        if not fuzzy_match_skills(skill, already_selected)
    ]

    if not candidates:
        return []

    # Get embedding for selected skills (combined) (ASYNC)
    selected_text = ", ".join(already_selected)
    selected_response = await client.embeddings.create(
        input=selected_text,
        model="text-embedding-ada-002"
    )
    selected_embedding = selected_response.data[0].embedding

    # Calculate similarity for each candidate
    similarities = []
    for candidate in candidates:
        candidate_response = await client.embeddings.create(
            input=candidate,
            model="text-embedding-ada-002"
        )
        candidate_embedding = candidate_response.data[0].embedding

        # Cosine similarity
        selected_vec = np.array(selected_embedding)
        candidate_vec = np.array(candidate_embedding)
        similarity = np.dot(selected_vec, candidate_vec) / (
            np.linalg.norm(selected_vec) * np.linalg.norm(candidate_vec)
        )

        similarities.append((candidate, similarity))

    # Sort by similarity (descending)
    similarities.sort(key=lambda x: x[1], reverse=True)

    # Return top N
    return [skill for skill, _ in similarities[:count]]


def arrange_technical_skills_logically(skills: List[str], skills_db: Dict[str, Dict[str, Any]]) -> List[str]:
    """
    Arrange technical skills in a logical order using category info from database.

    Args:
        skills: List of technical skills
        skills_db: Skills database with category information

    Returns:
        List[str]: Logically arranged skills
    """
    # Get skills with their order info
    skills_with_order = []

    for skill in skills:
        # Try to find skill in database (fuzzy match)
        skill_info = None
        for db_skill, info in skills_db.items():
            if fuzzy_match_skills(skill, [db_skill]):
                skill_info = info
                break

        if skill_info and isinstance(skill_info, dict):
            # Skill found in DB with category info
            order = skill_info.get("order", 999)  # Default to end if no order
            skills_with_order.append((skill, order))
        else:
            # Skill not in DB or no category info - put at end
            skills_with_order.append((skill, 999))

    # Sort by order, then alphabetically within same order
    skills_with_order.sort(key=lambda x: (x[1], x[0].lower()))

    # Return sorted skills
    return [skill for skill, _ in skills_with_order]


async def generate_skills_list(
    user_skills_db: Union[List[str], Dict[str, Dict[str, Any]]],
    job_data: Dict[str, Any],
    enhanced_experiences: List[Dict[str, Any]],
    client,
    essential_skills: List[str] = None,
    target_technical_skills: int = 25,
    num_soft_skills: int = 5
) -> Dict[str, Any]:
    """
    Generate optimized skills list for resume (ASYNC).

    Simple strategy:
    1. Add essential skills (mandatory)
    2. Add validated skills from bullets (mandatory)
    3. Add job-required skills from user DB (if needed)
    4. Add complementary skills from user DB (if needed)
    5. Arrange technical skills logically (using DB categories)
    6. Add soft skills at the end (mandatory)

    Args:
        user_skills_db: Skills from skills_DB.py (dict with categories or list)
        job_data: Structured job JSON
        enhanced_experiences: Adapted experiences with bullets
        client: AsyncOpenAI client for embeddings
        essential_skills: Skills to always include first (default: [])
        target_technical_skills: Target number of technical skills (default: 25)
        num_soft_skills: Number of soft skills to add (default: 5)

    Returns:
        Dict with skills list and metadata
    """
    print("\n" + "=" * 70)
    print("SKILLS LIST GENERATION (ASYNC)")
    print("=" * 70)

    # Handle both dict (new format) and list (old format) for backward compatibility
    if isinstance(user_skills_db, dict):
        skills_db_dict = user_skills_db
        skills_db_list = list(user_skills_db.keys())
    else:
        skills_db_dict = {}
        skills_db_list = user_skills_db

    essential_skills = essential_skills or []

    # Track added skills (case-insensitive deduplication)
    added_normalized = set()
    technical_skills = []

    def add_skill_if_new(skill: str) -> bool:
        """Add skill if not already added."""
        normalized = normalize_skill_name(skill)
        if normalized not in added_normalized:
            added_normalized.add(normalized)
            technical_skills.append(skill)
            return True
        return False

    # Step 1: Add essential skills (mandatory)
    print(f"\n[1/6] Adding essential skills...")
    essential_added = 0
    for skill in essential_skills:
        if add_skill_if_new(skill):
            essential_added += 1
    print(f"  Added: {essential_added}")

    # Step 2: Add validated skills from bullets (mandatory)
    print(f"\n[2/6] Adding validated skills from experiences...")
    validated_skills = extract_validated_skills(enhanced_experiences)
    validated_added = 0
    for skill in validated_skills:
        if add_skill_if_new(skill):
            validated_added += 1
    print(f"  Added: {validated_added}")

    current_count = len(technical_skills)
    print(f"\n  Current total: {current_count}/{target_technical_skills}")

    # Step 3: Add job-required skills if needed
    if current_count < target_technical_skills:
        print(f"\n[3/6] Adding job-required skills from your database...")
        job_skills = get_job_required_skills(job_data, skills_db_list)
        job_added = 0

        for skill in job_skills:
            if current_count >= target_technical_skills:
                break
            if add_skill_if_new(skill):
                job_added += 1
                current_count += 1

        print(f"  Added: {job_added}")
        print(f"  Current total: {current_count}/{target_technical_skills}")
    else:
        print(f"\n[3/6] Skipping job-required skills (target already reached)")
        job_added = 0

    # Step 4: Add complementary skills if still needed (ASYNC)
    if current_count < target_technical_skills:
        needed = target_technical_skills - current_count
        print(f"\n[4/6] Adding {needed} complementary skills (ASYNC)...")

        complementary_skills = await get_complementary_skills(
            already_selected=technical_skills,
            user_skills_db=skills_db_list,
            client=client,
            count=needed
        )

        complementary_added = 0
        for skill in complementary_skills:
            if add_skill_if_new(skill):
                complementary_added += 1

        print(f"  Added: {complementary_added}")
        print(f"  Current total: {len(technical_skills)}/{target_technical_skills}")
    else:
        print(f"\n[4/6] Skipping complementary skills (target already reached)")
        complementary_added = 0

    # Step 5: Arrange technical skills logically
    print(f"\n[5/6] Arranging technical skills logically...")
    technical_skills = arrange_technical_skills_logically(technical_skills, skills_db_dict)
    print(f"  Arranged {len(technical_skills)} skills")

    # Step 6: Add soft skills at the end (mandatory)
    print(f"\n[6/6] Adding soft skills...")
    soft_skills = job_data.get("soft_skills", [])[:num_soft_skills]
    print(f"  Added: {len(soft_skills)}")

    # Combine all skills
    all_skills = technical_skills + soft_skills

    # Print summary
    print("\n" + "=" * 70)
    print("[OK] SKILLS LIST COMPLETED (ASYNC)")
    print("=" * 70)
    print(f"\nBreakdown:")
    print(f"  Essential skills: {essential_added}")
    print(f"  Validated from bullets: {validated_added}")
    print(f"  Job-required: {job_added}")
    print(f"  Complementary: {complementary_added}")
    print(f"  Total Technical: {len(technical_skills)}")
    print(f"  Soft Skills: {len(soft_skills)}")
    print(f"  Grand Total: {len(all_skills)}")

    return {
        "skills": all_skills,
        "technical_skills": technical_skills,
        "soft_skills": soft_skills,
        "metadata": {
            "total_skills": len(all_skills),
            "technical_count": len(technical_skills),
            "soft_count": len(soft_skills),
            "essential_count": essential_added,
            "validated_count": validated_added,
            "job_required_count": job_added,
            "complementary_count": complementary_added,
            "target_technical_skills": target_technical_skills
        }
    }

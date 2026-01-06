"""
Profile Description Generator (Async Version)

Generates an authentic, logical, and ATS-friendly profile description
using a single GPT call.
"""

from typing import Dict, List, Any
import sys
from pathlib import Path

# Import gender processor, config loader, and user loader
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.gender_processor import clean_profile_description as clean_gender_brackets
from utils.config_loader import get_config
from utils.user_loader import get_user_gender, get_user_degree


async def check_role_semantic_match(job_title: str, experience_roles: List[str], client, threshold: float = 0.75) -> tuple:
    """
    Check if job title semantically matches any of the user's experience roles (ASYNC).

    Args:
        job_title: Target job title
        experience_roles: List of roles from user's experiences
        client: AsyncOpenAI client for embeddings
        threshold: Similarity threshold (default: 0.75)

    Returns:
        tuple: (is_match: bool, best_matching_role: str or None, similarity_score: float)
    """
    if not experience_roles:
        return False, None, 0.0

    # Get embedding for job title (ASYNC)
    job_embedding_response = await client.embeddings.create(
        input=job_title,
        model="text-embedding-ada-002"
    )
    job_embedding = job_embedding_response.data[0].embedding

    best_match = None
    best_score = 0.0

    # Compare with each experience role
    for role in experience_roles:
        role_embedding_response = await client.embeddings.create(
            input=role,
            model="text-embedding-ada-002"
        )
        role_embedding = role_embedding_response.data[0].embedding

        # Calculate cosine similarity
        import numpy as np
        job_vec = np.array(job_embedding)
        role_vec = np.array(role_embedding)

        similarity = np.dot(job_vec, role_vec) / (np.linalg.norm(job_vec) * np.linalg.norm(role_vec))

        if similarity > best_score:
            best_score = similarity
            best_match = role

    is_match = best_score >= threshold
    return is_match, best_match, best_score


async def generate_profile_description(
    job_data: Dict[str, Any],
    enhanced_experiences: List[Dict[str, Any]],
    skills_section: Dict[str, Any],
    client,
    gender: str = None
) -> Dict[str, Any]:
    """
    Generate professional profile description with authenticity validation (ASYNC).

    Features:
    - Auto-detects if experience should be ambiguous (2+ year jobs)
    - ONLY uses skills validated in actual experiences
    - Calculates skill overlap to prevent over-claiming
    - Returns authentic profile that matches actual capabilities
    - Formats with correct gender agreement

    Args:
        job_data: Structured job JSON
        enhanced_experiences: Adapted experiences with bullets
        skills_section: Generated skills list
        client: AsyncOpenAI client
        gender: User gender ('male' or 'female'), auto-detected if None

    Returns:
        Dict with profile text and metadata
    """
    print("\n" + "=" * 70)
    print("PROFILE DESCRIPTION GENERATION (ASYNC)")
    print("=" * 70)

    # Determine gender (use parameter or load from user config)
    if gender is None:
        gender = get_user_gender()

    print(f"\nUser Gender: {gender}")

    # Step 1: Determine experience strategy
    experience_required = job_data.get("experience_required", {}).get("years", "")
    use_ambiguous = any(x in experience_required.lower() for x in ["2+", "3+", "4+", "5+", "ans", "years"])

    strategy = "ambiguous" if use_ambiguous else "explicit"
    print(f"\n[Step 1/3] Experience strategy: {strategy}")
    if use_ambiguous:
        print(f"  Job requires: {experience_required}")
        print(f"  => Will use ambiguous competence terms (no explicit years)")

    # Step 2: Extract VALIDATED skills from actual experiences
    print("\n[Step 2/3] Extracting VALIDATED profile data...")

    # NEW: Collect ALL skills actually used in bullets (validated skills)
    validated_skills = set()
    for exp in enhanced_experiences:
        for bullet in exp.get("bullets", []):
            validated_skills.update(bullet.get("keywords_used", []))

    validated_skills = list(validated_skills)
    print(f"  Skills validated in bullets: {len(validated_skills)}")

    # NEW: Calculate job-to-candidate skill overlap
    job_must_have = set(job_data['technical_priorities']['must_have'])
    job_preferred = set(job_data['technical_priorities'].get('preferred', []))
    validated_set = set(validated_skills)

    must_have_overlap = job_must_have & validated_set
    preferred_overlap = job_preferred & validated_set

    overlap_ratio = len(must_have_overlap) / len(job_must_have) if job_must_have else 0

    print(f"  Must-have skill overlap: {len(must_have_overlap)}/{len(job_must_have)} ({overlap_ratio:.0%})")
    print(f"  Overlap skills: {', '.join(list(must_have_overlap)[:5])}")

    # NEW: Check if job role matches user's experience roles (semantic matching)
    print(f"\n  Role matching analysis:")
    experience_roles = [exp.get('role', '') for exp in enhanced_experiences if exp.get('role')]
    job_title = job_data['job_title']

    print(f"  Job title: {job_title}")
    print(f"  User's experience roles: {', '.join(experience_roles)}")

    role_matches, matched_role, match_score = await check_role_semantic_match(
        job_title=job_title,
        experience_roles=experience_roles,
        client=client,
        threshold=0.75
    )

    print(f"  Best matching role: {matched_role} (similarity: {match_score:.2%})")

    if role_matches:
        # Use job role directly
        role_strategy = "direct_job_role"
        profile_role = job_title
        bridging_phrase = None
        print(f"  => Strategy: Use job role directly ('{job_title}')")
    else:
        # Use user's real background + bridging phrase
        role_strategy = "user_background_with_bridge"
        # Get last experience role or use degree
        profile_role = experience_roles[-1] if experience_roles else get_user_degree()

        # Determine bridging phrase based on context
        domains = []
        for exp in enhanced_experiences:
            context = exp.get("context", "")
            if "conseil" in context.lower() or "consulting" in context.lower():
                domains.append("consulting")
            if "transformation" in context.lower():
                domains.append("transformation digitale")

        if domains:
            bridging_phrase = f"avec une expérience en {' et '.join(set(domains))}"
        else:
            # Use top validated skills as bridge
            top_bridge_skills = list(must_have_overlap)[:3] if must_have_overlap else validated_skills[:3]
            bridging_phrase = f"avec une maîtrise de {', '.join(top_bridge_skills)}"

        print(f"  => Strategy: Use user's background ('{profile_role}') + bridge ('{bridging_phrase}')")

    # NEW: Determine authenticity mode based on overlap
    if overlap_ratio >= 0.7:
        authenticity_mode = "high_match"  # Can be aggressive with ATS
        print(f"  => Authenticity mode: HIGH MATCH (can optimize for ATS)")
    elif overlap_ratio >= 0.4:
        authenticity_mode = "moderate_match"  # Balanced approach
        print(f"  => Authenticity mode: MODERATE MATCH (balanced ATS + authenticity)")
    else:
        authenticity_mode = "low_match"  # Focus on authenticity, not job keywords
        print(f"  => Authenticity mode: LOW MATCH (prioritize authenticity over ATS)")

    # Get top technical skills - ONLY from validated skills
    # FIX: Use correct field name "technical_skills" instead of non-existent "technical_skills_from_job"
    top_skills = [s for s in skills_section.get("technical_skills", [])[:8] if s in validated_set][:5]
    print(f"  Top validated skills to highlight: {', '.join(top_skills[:3]) if top_skills else 'None'}...")

    # Get key achievements from highest ATS score bullets
    all_bullets = []
    for exp in enhanced_experiences:
        for bullet in exp.get("bullets", []):
            all_bullets.append({
                "text": bullet["text"],
                "ats_score": bullet.get("ats_score", 0),
                "project": exp["project_name"]
            })

    # Sort by ATS score and get top 2-3 achievements
    all_bullets.sort(key=lambda x: x["ats_score"], reverse=True)
    top_achievements = all_bullets[:3]
    print(f"  Key achievements identified: {len(top_achievements)}")

    # NEW: Extract domain expertise DYNAMICALLY from selected experiences
    user_domains = []
    for exp in enhanced_experiences:
        exp_domains = exp.get("domains", [])
        user_domains.extend(exp_domains)

    user_domains = list(set(user_domains))  # Remove duplicates
    print(f"  User's domain expertise: {', '.join(user_domains) if user_domains else 'technical'}")

    # NEW: Check which domains are relevant to the job (ATS matching)
    # Build job text from multiple sources
    job_text = " ".join([
        job_data.get("job_title", ""),
        " ".join(job_data.get("responsibilities", [])),
        " ".join(job_data.get("keywords", [])),
        job_data.get("company_description", ""),
        " ".join(job_data.get("technical_skills", []))
    ]).lower()

    # Filter domains - check if domain appears in job text (case-insensitive)
    ats_relevant_domains = []
    for domain in user_domains:
        # Simple substring check (case-insensitive)
        # This works for most domains like "consulting", "R&D", "data science", etc.
        if domain.lower() in job_text:
            ats_relevant_domains.append(domain)
            print(f"  [+] Domain '{domain}' is ATS-relevant (found in job)")
        else:
            print(f"  [-] Domain '{domain}' is NOT ATS-relevant (not in job)")

    domains = ats_relevant_domains
    print(f"  ATS-relevant domains: {', '.join(domains) if domains else 'none'}")

    # Get education level
    education_level = job_data.get("education_required", {}).get("level", "")

    # Get language
    language = job_data["metadata"]["language"]

    # Step 3: Build GPT prompt
    print("\n[Step 3/3] Generating profile with GPT (ASYNC)...")

    # Build system prompt
    lang_instructions = {
        "fr": {
            "ambiguous_terms": "expert, spécialisé, maîtrise, expérience confirmée, compétences avérées",
            "structure": "[Titre/Rôle] + [Spécialisation] + [Compétences clés] + [Valeur ajoutée]",
            "example": "Expert en Data Science spécialisé en Intelligence Artificielle et transformation digitale. Maîtrise de Python, Azure et LangChain pour développer des solutions d'IA générative. Passionné par l'accompagnement client et l'innovation."
        },
        "en": {
            "ambiguous_terms": "expert, specialized, proficient, proven experience, demonstrated skills",
            "structure": "[Role/Title] + [Specialization] + [Key Skills] + [Value Proposition]",
            "example": "Data Science expert specialized in Artificial Intelligence and digital transformation. Proficient in Python, Azure, and LangChain for developing generative AI solutions. Passionate about client support and innovation."
        }
    }

    lang_config = lang_instructions.get(language, lang_instructions["fr"])

    # Gender instructions
    gender_instructions = {
        "male": {
            "fr": "masculin (ex: 'Consultant expert', 'spécialisé', 'expérimenté')",
            "en": "male (ex: 'experienced', 'specialized')"
        },
        "female": {
            "fr": "féminin (ex: 'Consultante experte', 'spécialisée', 'expérimentée')",
            "en": "female (ex: 'experienced', 'specialized')"
        }
    }

    gender_format = gender_instructions.get(gender, gender_instructions["male"]).get(language, "")

    system_prompt = f"""You are an expert resume writer creating professional profile descriptions.

MISSION: Generate a compelling, ATS-optimized profile description in {language.upper()}.

CRITICAL RULES:
1. Length: 2-3 sentences, 50-100 words
2. Structure: {lang_config['structure']}
3. Tone: Professional, confident, authentic (not generic)
4. Experience Strategy: {strategy.upper()}
5. Gender Agreement: {gender_format}
6. Role Strategy: {role_strategy.upper()}

GENDER FORMATTING:
- User gender: {gender}
- ALL adjectives, past participles, and job titles MUST agree with {gender_format}
- If job description uses neutral format like "consultant(e)" or "expert(e)", remove parentheses and use correct gender form
- Examples in French:
  * Male: "Consultant expert spécialisé en Data Science"
  * Female: "Consultante experte spécialisée en Data Science"
- DO NOT use gender-neutral formats with parentheses like "(e)"

ROLE STRATEGY - {role_strategy.upper()}:
"""

    if role_strategy == "direct_job_role":
        system_prompt += f"""
- User's experience roles MATCH the job title semantically
- START profile with the job title/role: "{profile_role}"
- Format: "[Job Role] spécialisé en [domain/specialization]..."
- Example (FR): "Consultant Data Science et IA spécialisé en transformation digitale..."
- Example (EN): "Data Science and AI Consultant specialized in digital transformation..."
- This establishes immediate alignment with the job requirements
"""
    else:  # user_background_with_bridge
        system_prompt += f"""
- User's experience roles DO NOT match the job title semantically
- START with user's REAL background: "{profile_role}"
- THEN add bridging phrase: "{bridging_phrase}"
- Format: "[User's Real Role] [bridging phrase], spécialisé en [skills]..."
- Example (FR): "Ingénieur en IA et Data Science avec une expérience en consulting et transformation digitale, spécialisé en..."
- Example (EN): "AI and Data Science Engineer with experience in consulting and digital transformation, specialized in..."
- This maintains authenticity while showing relevance to the job

IMPORTANT - Domain Mentions:
- ONLY mention domains that are ATS-RELEVANT (appear in the provided list)
- If no ATS-relevant domains are provided, focus on technical skills instead
- DO NOT force domain mentions if they don't help with ATS matching
"""

    system_prompt += f"""
EXPERIENCE STRATEGY - {strategy.upper()}:
"""

    if strategy == "ambiguous":
        system_prompt += f"""- DO NOT mention explicit years of experience
- USE ambiguous competence terms: {lang_config['ambiguous_terms']}
- Focus on WHAT the candidate can do, not HOW LONG
- Demonstrate competence through skills and achievements
- NEVER use terms like "junior", "débutant", "recent graduate"

CORRECT: "Expert en Data Science spécialisé en IA..."
WRONG: "Data Scientist avec 2 ans d'expérience..."
"""
    else:
        system_prompt += f"""- You MAY mention years if provided
- Focus on concrete experience and achievements
"""

    # NEW: Different instructions based on authenticity mode
    if authenticity_mode == "high_match":
        system_prompt += f"""
ATS OPTIMIZATION (HIGH MATCH MODE - Overlap: {overlap_ratio:.0%}):
- The candidate has strong skill overlap with job requirements
- Include must-have job keywords naturally
- Use exact job terminology when it matches candidate skills
- Integrate validated technical skills organically

AUTHENTICITY RULES:
- ONLY mention skills from the VALIDATED SKILLS list (not all job requirements)
- Reference actual project domains from candidate experiences
- If a job keyword is NOT in validated skills, DO NOT mention it
- Avoid generic phrases like "hard worker" or "team player"
"""
    elif authenticity_mode == "moderate_match":
        system_prompt += f"""
BALANCED APPROACH (MODERATE MATCH MODE - Overlap: {overlap_ratio:.0%}):
- The candidate has partial overlap with job requirements
- Focus on candidate's ACTUAL strengths (validated skills)
- Include job keywords ONLY if they appear in validated skills
- Describe the candidate's real expertise, not the job description
- focus on things that are required for the job and the user have

AUTHENTICITY RULES:
- ONLY mention skills from the VALIDATED SKILLS list
- Emphasize what the candidate ACTUALLY does well
- Reference real project domains and contexts
- DO NOT force-fit job keywords that aren't validated
"""


    system_prompt += f"""
Example format - THIS EXAMPLE IS IN {'ENGLISH' if language == 'en' else 'FRENCH'} (FOLLOW THIS LANGUAGE):
{lang_config['example']}

REMINDER: You must write your entire profile in {'ENGLISH' if language == 'en' else 'FRENCH'} only, just like the example above.
"""

    # Build user prompt - CRITICAL: Only provide validated data
    user_prompt = f"""LANGUAGE: YOU MUST WRITE THIS ENTIRE PROFILE IN {'ENGLISH' if language == 'en' else 'FRENCH'} ONLY. NO MIXING.

Generate a profile description for this candidate:

JOB TARGET (for context only):
- Title: {job_data['job_title']}
- Company: {job_data['company_name']}

ROLE STRATEGY: {role_strategy.upper()}
- Profile role to use: "{profile_role}"
"""

    if role_strategy == "user_background_with_bridge":
        user_prompt += f"""- Bridging phrase: "{bridging_phrase}"
- IMPORTANT: Start with "{profile_role} {bridging_phrase}, spécialisé en..."
"""
    else:
        user_prompt += f"""- IMPORTANT: Start with "{profile_role} spécialisé en..."
"""

    user_prompt += f"""
AUTHENTICITY MODE: {authenticity_mode.upper()}
Skill Overlap with Job: {overlap_ratio:.0%} ({len(must_have_overlap)}/{len(job_must_have)} must-have skills)

Role Semantic Match: {"YES - Use job title directly" if role_matches else f"NO - Use user's background (similarity: {match_score:.0%})"}

VALIDATED SKILLS (ONLY use skills from this list - these are PROVEN in actual work):
- Technical: {', '.join(top_skills) if top_skills else 'None from job requirements'}
- All validated: {', '.join(validated_skills[:10])}
- Soft skills: {', '.join(job_data['soft_skills'][:3])}

DOMAINS TO MENTION (ATS-RELEVANT ONLY):
- ATS-relevant domains (MENTION THESE): {', '.join(domains) if domains else 'NONE - Do not mention domains, focus on technical skills'}
- User has other domains but they are NOT in the job offer, so DO NOT mention them
- Expertise areas for reference: {', '.join(set([exp.get('role', 'Engineer') for exp in enhanced_experiences]))}

CANDIDATE ACHIEVEMENTS (from actual projects - reference these):
"""

    for i, achievement in enumerate(top_achievements, 1):
        user_prompt += f"\n{i}. {achievement['text'][:80]}... (from {achievement['project']})"

    if education_level:
        user_prompt += f"\n\nEDUCATION: {education_level}"

    user_prompt += f"""

EXPERIENCE STRATEGY: {strategy}
"""

    if strategy == "ambiguous":
        user_prompt += f"""
REMEMBER: Do NOT state years. Use terms like: {lang_config['ambiguous_terms']}
"""

    # Different instructions based on authenticity mode
    if authenticity_mode == "high_match":
        user_prompt += f"""
INSTRUCTIONS (HIGH MATCH - {overlap_ratio:.0%} overlap):
You have strong skill overlap! Write a compelling profile that:
1. Highlights the candidate's validated skills that MATCH the job
2. Uses job terminology where it aligns with candidate's expertise
3. Emphasizes the {len(must_have_overlap)} must-have skills the candidate actually has
4. Stays authentic - only mention skills from VALIDATED SKILLS list

CRITICAL LANGUAGE REQUIREMENT:
- You MUST write the ENTIRE profile in {'ENGLISH' if language == 'en' else 'FRENCH'} language ONLY
- Use {'ENGLISH' if language == 'en' else 'FRENCH'} words, grammar, and vocabulary throughout
- Do NOT mix languages or use words from other languages

Generate profile (2-3 sentences, 50-100 words). Return ONLY the text in {'ENGLISH' if language == 'en' else 'FRENCH'}.
"""
    elif authenticity_mode == "moderate_match":
        user_prompt += f"""
INSTRUCTIONS (MODERATE MATCH - {overlap_ratio:.0%} overlap):
You have partial overlap. Write an authentic profile that:
1. Focuses on the candidate's REAL strengths (validated skills)
2. Mentions the {len(must_have_overlap)} overlapping must-have skills naturally
3. Describes the candidate's actual expertise areas honestly
4. DO NOT claim job skills that aren't in validated skills list

CRITICAL LANGUAGE REQUIREMENT:
- You MUST write the ENTIRE profile in {'ENGLISH' if language == 'en' else 'FRENCH'} language ONLY
- Use {'ENGLISH' if language == 'en' else 'FRENCH'} words, grammar, and vocabulary throughout
- Do NOT mix languages or use words from other languages

Generate profile (2-3 sentences, 50-100 words). Return ONLY the text in {'ENGLISH' if language == 'en' else 'FRENCH'}.
"""


    # Call OpenAI (ASYNC)
    # Fallback chain: task-specific → module default → global default
    model = (get_config('enhancing.profile_generation.model') or
             get_config('enhancing.default_model') or
             get_config('openai.default_model', 'gpt-4o-mini'))

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=get_config('enhancing.profile_generation.temperature', 0.7),
        max_tokens=200
    )

    profile_text = response.choices[0].message.content.strip()
    word_count = len(profile_text.split())

    # Extract keywords used in profile (simple check)
    keywords_included = []
    all_keywords = job_data.get("keywords", []) + job_data.get("technical_skills", [])
    for keyword in all_keywords:
        if keyword.lower() in profile_text.lower():
            keywords_included.append(keyword)

    # NEW: Validate authenticity - check if any unvalidated skills were mentioned
    unvalidated_claims = []
    job_skills_mentioned = []
    for skill in job_data.get("technical_skills", []):
        if skill.lower() in profile_text.lower():
            job_skills_mentioned.append(skill)
            if skill not in validated_set:
                unvalidated_claims.append(skill)

    authenticity_score = 1.0 - (len(unvalidated_claims) / max(len(job_skills_mentioned), 1))

    # Print summary
    print("\n" + "=" * 70)
    print("[OK] PROFILE DESCRIPTION GENERATED (ASYNC)")
    print("=" * 70)
    print(f"\nProfile:")
    print(f'  "{profile_text}"')
    print(f"\nMetadata:")
    print(f"  Words: {word_count}")
    print(f"  Strategy: {strategy}")
    print(f"  Role strategy: {role_strategy}")
    print(f"  Profile role: {profile_role}")
    if role_strategy == "user_background_with_bridge":
        print(f"  Bridging phrase: {bridging_phrase}")
    print(f"  Role semantic match: {match_score:.0%}")
    print(f"  ATS-relevant domains: {len(domains)}/{len(user_domains)} ({', '.join(domains) if domains else 'none'})")
    print(f"  Authenticity mode: {authenticity_mode}")
    print(f"  Skill overlap: {overlap_ratio:.0%}")
    print(f"  Job skills mentioned: {len(job_skills_mentioned)}")
    print(f"  Validated mentions: {len(job_skills_mentioned) - len(unvalidated_claims)}/{len(job_skills_mentioned)}")
    if unvalidated_claims:
        print(f"  [!] WARNING: Unvalidated claims: {', '.join(unvalidated_claims)}")
    print(f"  Authenticity score: {authenticity_score:.0%}")

    return {
        "text": profile_text,
        "metadata": {
            "experience_strategy": strategy,
            "role_strategy": role_strategy,  # NEW
            "profile_role": profile_role,  # NEW
            "bridging_phrase": bridging_phrase if role_strategy == "user_background_with_bridge" else None,  # NEW
            "role_semantic_match_score": match_score,  # NEW
            "ats_relevant_domains": domains,  # NEW
            "all_user_domains": user_domains,  # NEW
            "authenticity_mode": authenticity_mode,
            "skill_overlap_ratio": overlap_ratio,
            "validated_skills_count": len(validated_skills),
            "must_have_overlap_count": len(must_have_overlap),
            "unvalidated_claims": unvalidated_claims,
            "authenticity_score": authenticity_score,
            "word_count": word_count,
            "keywords_included": keywords_included,
            "keywords_count": len(keywords_included),
            "language": language,
            "gender": gender,
            "education_mentioned": education_level in profile_text if education_level else False
        }
    }

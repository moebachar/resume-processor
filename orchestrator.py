"""
Async Resume Processing Orchestrator - Production Microservice Version

JSON-only pipeline optimized for high-concurrency deployment.
Supports dynamic experience configuration with direct/enhanced strategies.
Returns resume and cover letter data in JSON format (no PDF generation).
"""

import asyncio
import os
import time
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import async modules
from modules.structuring.main import structure_job_description
from modules.enhancing.coordinator import coordinate_experiences
from modules.enhancing.bullet_coordinator import generate_bullets_with_coordinator
from modules.enhancing.profile_generator import generate_profile_description
from modules.enhancing.skills_generator import generate_skills_list
from modules.enhancing.direct_extractor import extract_direct_experience
from modules.cover_letter.generator import generate_cover_letter


async def process_resume_pipeline(
    user_json: Dict[str, Any],
    config_json: Dict[str, Any],
    job_text: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process entire resume pipeline asynchronously.

    This is the CORE function for the microservice.
    Optimized for maximum parallelization and high concurrency.
    Supports dynamic experience configuration with direct/enhanced strategies.
    Returns JSON-only output (no PDF generation).

    Args:
        user_json: User data containing:
            - personal: Personal info
            - contact: Contact info
            - projects_database: Available projects
            - skills_database: User skills
            - experiences_config: List of experience configurations (NEW)
              Each config has:
                - candidate_projects: List of project names
                - role_strategy: "direct" | "enhanced"
                - content_strategy: "direct" | "enhanced"
            - education: Education list
            - languages: Languages list
        config_json: Configuration (models, profiles, settings)
        job_text: Raw job description text
        api_key: OpenAI API key (optional, uses env var if not provided)

    Returns:
        Dict with:
            - success: bool
            - structured_job: dict
            - resume: dict (personal, experience, skills, education, etc.)
            - cover_letter: str
            - metadata: dict (timing, stats, etc.)
    """
    print("\n" + "=" * 80)
    print("ASYNC RESUME PROCESSING PIPELINE - DYNAMIC EXPERIENCES")
    print("=" * 80)

    start_time = time.time()

    # Get API key
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {
            "success": False,
            "error": "OPENAI_API_KEY not found"
        }

    # Initialize AsyncOpenAI client (shared across all calls)
    client = AsyncOpenAI(api_key=api_key)

    # Extract configuration
    projects_database = user_json.get("projects_database", {})
    skills_database = user_json.get("skills_database", {})
    skills = skills_database.get("skills", {})
    essential_skills = skills_database.get("essential_skills", [])
    user_info = user_json.get("personal", {})
    contact_info = user_json.get("contact", {})
    experiences_config_raw = user_json.get("experiences_config", [])

    # Validate experiences_config
    if not experiences_config_raw:
        return {
            "success": False,
            "error": "experiences_config is required in user_json"
        }

    # Create ordered list of project names for index resolution
    project_names = list(projects_database.keys())
    print(f"\nProjects available ({len(project_names)}):")
    for i, name in enumerate(project_names):
        print(f"  [{i}] {name}")

    # Resolve project indexes to names in experiences_config
    experiences_config = []
    for i, exp_config in enumerate(experiences_config_raw):
        candidate_indexes = exp_config.get("candidate_projects", [])

        # Convert indexes to project names
        candidate_names = []
        for idx in candidate_indexes:
            if not isinstance(idx, int):
                return {
                    "success": False,
                    "error": f"Experience {i}: candidate_projects must be integers (indexes), got {type(idx).__name__}"
                }
            if idx < 0 or idx >= len(project_names):
                return {
                    "success": False,
                    "error": f"Experience {i}: project index {idx} out of range (0-{len(project_names)-1})"
                }
            candidate_names.append(project_names[idx])

        # Create resolved config
        experiences_config.append({
            "candidate_projects": candidate_names,
            "role_strategy": exp_config.get("role_strategy", "enhanced"),
            "content_strategy": exp_config.get("content_strategy", "enhanced")
        })

    print(f"\nResolved experiences config:")
    for i, exp in enumerate(experiences_config):
        print(f"  Exp {i}: {exp['candidate_projects']} | role:{exp['role_strategy']} content:{exp['content_strategy']}")

    # Get enhancement config
    enhancement_config = config_json.get("enhancing", {})
    num_bullets = enhancement_config.get("bullet_adaptation", {}).get("bullets_per_experience", 4)
    max_bullet_length = enhancement_config.get("bullet_adaptation", {}).get("max_bullet_length", 150)
    target_technical_skills = enhancement_config.get("skills_generation", {}).get("target_technical_skills", 25)
    num_soft_skills = enhancement_config.get("skills_generation", {}).get("num_soft_skills", 5)

    # Get model config
    structuring_model = config_json.get("structuring", {}).get("model") or config_json.get("openai", {}).get("default_model", "gpt-4o-mini")
    coordinator_model = enhancement_config.get("coordinator", {}).get("model") or config_json.get("openai", {}).get("default_model", "gpt-4o-mini")
    bullet_model = enhancement_config.get("bullet_coordinator", {}).get("model") or config_json.get("openai", {}).get("default_model", "gpt-4o-mini")
    profile_model = enhancement_config.get("profile_generation", {}).get("model") or config_json.get("openai", {}).get("default_model", "gpt-4o-mini")
    cover_letter_model = enhancement_config.get("cover_letter", {}).get("model") or config_json.get("openai", {}).get("default_model", "gpt-4o-mini")

    try:
        # =================================================================
        # STEP 1: STRUCTURE JOB DESCRIPTION (1 async call)
        # =================================================================
        print(f"\n[STEP 1] Structuring job description... (model: {structuring_model})")
        step1_start = time.time()

        structuring_result = await structure_job_description(
            job_text=job_text,
            source_url="",
            api_key=api_key,
            model=structuring_model
        )

        if not structuring_result["success"]:
            return {
                "success": False,
                "error": f"Structuring failed: {structuring_result.get('error')}"
            }

        structured_job = structuring_result["data"]
        language = structured_job["metadata"]["language"]
        step1_time = time.time() - step1_start
        print(f"  [OK] Completed in {step1_time:.2f}s")
        print(f"  Job: {structured_job['job_title']} at {structured_job['company_name']}")
        print(f"  Language: {language}")

        # =================================================================
        # STEP 2: COORDINATOR - PROCESS EXPERIENCE CONFIGURATIONS
        # =================================================================
        print(f"\n[STEP 2] Experience coordination... (model: {coordinator_model})")
        step2_start = time.time()

        coordinator_result = await coordinate_experiences(
            experiences_config=experiences_config,
            projects_database=projects_database,
            job_data=structured_job,
            client=client,
            model=coordinator_model
        )

        selected_experiences = coordinator_result["selected_experiences"]
        step2_time = time.time() - step2_start
        print(f"  [OK] Completed in {step2_time:.2f}s")
        print(f"  Coordinated {len(selected_experiences)} experiences")

        # =================================================================
        # STEP 3: CONDITIONAL ENHANCEMENT (PARALLEL FOR ENHANCED ONLY)
        # =================================================================
        print(f"\n[STEP 3] Content generation (conditional)...")
        step3_start = time.time()

        # Separate enhanced and direct experiences
        enhanced_tasks = []
        enhanced_indices = []
        direct_results = []

        for exp_strategy in selected_experiences:
            exp_index = exp_strategy["experience_index"]
            project_name = exp_strategy["selected_project"]
            project_data = projects_database[project_name]

            if exp_strategy["content_strategy"] == "enhanced":
                # Create async task for enhanced bullet generation
                task = generate_bullets_with_coordinator(
                    project_name=project_name,
                    project_data=project_data,
                    job_data=structured_job,
                    coordinator_instructions={
                        "project_name": project_name,
                        "target_role": exp_strategy["role_title"],
                        "keywords_to_use": exp_strategy["keywords_to_use"],
                        "enhancement_level": exp_strategy["enhancement_level"],
                        "responsibilities_to_incorporate": exp_strategy["responsibilities_to_incorporate"]
                    },
                    client=client,
                    num_bullets=num_bullets,
                    max_bullet_length=max_bullet_length,
                    model=bullet_model,
                    temperature=enhancement_config.get("bullet_coordinator", {}).get("temperature", 0.6)
                )
                enhanced_tasks.append(task)
                enhanced_indices.append(exp_index)
            else:
                # Extract direct experience (no AI call needed)
                direct_exp = extract_direct_experience(
                    project_name=project_name,
                    project_data=project_data,
                    role_title=exp_strategy["role_title"],
                    language=language
                )
                direct_results.append((exp_index, direct_exp))

        # Run enhanced bullet generation in parallel
        enhanced_results = []
        if enhanced_tasks:
            print(f"  Generating {len(enhanced_tasks)} enhanced experiences in parallel...")
            enhanced_results = await asyncio.gather(*enhanced_tasks)
            print(f"  [OK] Enhanced bullets completed")

        if direct_results:
            print(f"  Extracted {len(direct_results)} direct experiences")

        # Merge results in original order
        all_experience_results = {}

        # Add enhanced results
        for idx, result in zip(enhanced_indices, enhanced_results):
            all_experience_results[idx] = result

        # Add direct results
        for idx, result in direct_results:
            all_experience_results[idx] = result

        # Sort by index to maintain order
        bullet_results = [all_experience_results[i] for i in sorted(all_experience_results.keys())]

        # Generate skills (consider both enhanced and direct)
        skills_result = await generate_skills_list(
            user_skills_db=skills,
            job_data=structured_job,
            enhanced_experiences=bullet_results,
            client=client,
            essential_skills=essential_skills,
            target_technical_skills=target_technical_skills,
            num_soft_skills=num_soft_skills
        )

        # Generate profile
        profile_result = await generate_profile_description(
            job_data=structured_job,
            enhanced_experiences=bullet_results,
            skills_section=skills_result,
            client=client,
            gender=user_info.get("gender")
        )

        step3_time = time.time() - step3_start
        print(f"  [OK] Content generation completed in {step3_time:.2f}s")

        # =================================================================
        # STEP 4: GENERATE COVER LETTER (1 async call)
        # =================================================================
        print(f"\n[STEP 4] Generating cover letter...")
        step4_start = time.time()

        cover_letter_result = await generate_cover_letter(
            job_data=structured_job,
            enhanced_experiences=bullet_results,
            profile_text=profile_result["text"],
            skills=skills_result["technical_skills"],
            client=client,
            model=cover_letter_model
        )

        step4_time = time.time() - step4_start

        if cover_letter_result["success"]:
            print(f"  [OK] Cover letter completed in {step4_time:.2f}s")
        else:
            print(f"  [WARNING] Cover letter generation failed: {cover_letter_result.get('error')}")

        # =================================================================
        # STEP 5: BUILD RESUME JSON OUTPUT
        # =================================================================
        print(f"\n[STEP 5] Building resume JSON...")
        step5_start = time.time()

        # Helper function to extract language-specific strings
        def extract_lang(value, lang):
            """Extract language-specific string from object or return as-is if string"""
            if isinstance(value, dict) and lang in value:
                return value[lang]
            elif isinstance(value, dict):
                return next(iter(value.values()), "")
            return value

        # Build experiences list
        final_experiences = []
        for i, bullet_result in enumerate(bullet_results):
            project_name = bullet_result["project_name"]
            project_data = projects_database[project_name]

            # Format bullets as array of strings
            bullets_array = [b["text"] for b in bullet_result["bullets"]]

            # Check if this is a direct or enhanced experience
            is_direct = bullet_result.get("is_direct", False)

            exp_entry = {
                "role": bullet_result["role"],
                "company": project_data.get("company", user_info.get("name", "Freelance")),
                "location": extract_lang(project_data.get("location", {}), language) or "Remote",
                "start_date": project_data.get("start_date", "2023-01"),
                "end_date": project_data.get("end_date", "2024-12"),
                "bullets": bullets_array,
                "context": project_data.get("contexte", ""),
                "is_direct": is_direct  # Include flag for transparency
            }
            final_experiences.append(exp_entry)

        # Transform education section
        education_list = []
        for edu in user_json.get("education", []):
            education_list.append({
                "degree": extract_lang(edu.get("degree", ""), language),
                "institution": edu.get("institution", ""),
                "location": extract_lang(edu.get("location", ""), language),
                "start_date": edu.get("start", ""),
                "end_date": edu.get("end", ""),
                "description": extract_lang(edu.get("description", ""), language)
            })

        # Transform languages section
        languages_list = []
        for lang_item in user_json.get("languages", []):
            languages_list.append({
                "language": extract_lang(lang_item.get("language", ""), language),
                "proficiency": extract_lang(lang_item.get("proficiency", ""), language)
            })

        # Build complete resume JSON
        resume_json = {
            "personal": {
                "name": user_info.get("name", ""),
                "title": user_info.get("title", ""),
                "degree": user_info.get("degree", "")
            },
            "contact": contact_info,
            "profile": profile_result["text"],
            "experience": final_experiences,
            "skills": {
                "technical": skills_result["technical_skills"],
                "soft": skills_result["soft_skills"]
            },
            "education": education_list,
            "certifications": user_json.get("certifications", []),
            "languages": languages_list
        }

        step5_time = time.time() - step5_start
        print(f"  [OK] Resume JSON built in {step5_time:.2f}s")

        # =================================================================
        # FINAL: CALCULATE STATS & RETURN
        # =================================================================
        total_time = time.time() - start_time

        print("\n" + "=" * 80)
        print("PIPELINE COMPLETED")
        print("=" * 80)
        print(f"\nTiming Breakdown:")
        print(f"  Step 1 (Structuring):       {step1_time:6.2f}s")
        print(f"  Step 2 (Coordinator):       {step2_time:6.2f}s")
        print(f"  Step 3 (Content Gen):       {step3_time:6.2f}s")
        print(f"  Step 4 (Cover Letter):      {step4_time:6.2f}s")
        print(f"  Step 5 (JSON Build):        {step5_time:6.2f}s")
        print(f"  {'-' * 40}")
        print(f"  TOTAL:                      {total_time:6.2f}s")

        # Calculate average ATS score (only for enhanced experiences)
        enhanced_ats_scores = [
            br["average_ats_score"]
            for br in bullet_results
            if not br.get("is_direct", False)
        ]
        avg_ats_score = sum(enhanced_ats_scores) / len(enhanced_ats_scores) if enhanced_ats_scores else 0

        # Count direct vs enhanced
        num_direct = sum(1 for br in bullet_results if br.get("is_direct", False))
        num_enhanced = len(bullet_results) - num_direct

        return {
            "success": True,
            "structured_job": structured_job,
            "resume": resume_json,
            "cover_letter": cover_letter_result.get("cover_letter_body") if cover_letter_result["success"] else None,
            "metadata": {
                "processing_time_seconds": round(total_time, 2),
                "timing_breakdown": {
                    "structuring": round(step1_time, 2),
                    "coordinator": round(step2_time, 2),
                    "content_generation": round(step3_time, 2),
                    "cover_letter": round(step4_time, 2),
                    "json_build": round(step5_time, 2)
                },
                "language": language,
                "experiences": {
                    "total": len(bullet_results),
                    "enhanced": num_enhanced,
                    "direct": num_direct,
                    "projects_used": [br["project_name"] for br in bullet_results]
                },
                "average_ats_score": round(avg_ats_score, 2),
                "total_skills": skills_result['metadata']['total_skills'],
                "cover_letter_word_count": cover_letter_result.get("metadata", {}).get("word_count", 0) if cover_letter_result["success"] else 0
            }
        }

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "error": str(e)
        }

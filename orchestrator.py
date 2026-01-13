"""
Async Resume Processing Orchestrator - Production Microservice Version

JSON-only pipeline optimized for high-concurrency deployment.
Returns resume and cover letter data in JSON format (no PDF generation).
"""

import asyncio
import os
import time
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import async modules with updated paths
from modules.structuring.main import structure_job_description
from modules.enhancing.coordinator import coordinate_enhancement
from modules.enhancing.bullet_coordinator import generate_bullets_with_coordinator
from modules.enhancing.profile_generator import generate_profile_description
from modules.enhancing.skills_generator import generate_skills_list
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
    Returns JSON-only output (no PDF generation).

    Args:
        user_json: User data (personal info, projects, skills, etc.)
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
    print("ASYNC RESUME PROCESSING PIPELINE - JSON OUTPUT")
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
        step1_time = time.time() - step1_start
        print(f"  [OK] Completed in {step1_time:.2f}s")
        print(f"  Job: {structured_job['job_title']} at {structured_job['company_name']}")
        print(f"  Language: {structured_job['metadata']['language']}")

        # =================================================================
        # STEP 2: COORDINATOR - SELECT PROJECTS & PLAN (1 async call)
        # =================================================================
        print(f"\n[STEP 2] Coordinator planning... (model: {coordinator_model})")
        step2_start = time.time()

        coordinator_strategy = await coordinate_enhancement(
            projects_database=projects_database,
            job_data=structured_job,
            client=client,
            model=coordinator_model
        )

        selected_projects = coordinator_strategy["selected_projects"]
        step2_time = time.time() - step2_start
        print(f"  [OK] Completed in {step2_time:.2f}s")
        print(f"  Selected {len(selected_projects)} projects")

        # =================================================================
        # STEP 3: PARALLEL BULLETS + SEQUENTIAL SKILLS/PROFILE
        # =================================================================
        print(f"\n[STEP 3] Enhancement generation...")
        step3_start = time.time()

        # Task 1-3: Generate bullets for each project (parallel)
        tasks = []
        for project_plan in selected_projects:
            project_name = project_plan["project_name"]
            project_data = projects_database[project_name]

            task = generate_bullets_with_coordinator(
                project_name=project_name,
                project_data=project_data,
                job_data=structured_job,
                coordinator_instructions=project_plan,
                client=client,
                num_bullets=num_bullets,
                max_bullet_length=max_bullet_length,
                model=bullet_model,
                temperature=enhancement_config.get("bullet_coordinator", {}).get("temperature", 0.6)
            )
            tasks.append(task)

        # Run bullet generation in parallel
        print(f"  Executing {len(tasks)} bullet generations in parallel...")
        bullet_results = await asyncio.gather(*tasks)
        print(f"  [OK] Bullets completed")

        # Generate skills
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
        print(f"  [OK] Enhancement completed in {step3_time:.2f}s")

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

        language = structured_job["metadata"]["language"]

        # Helper function to extract language-specific strings
        def extract_lang(value, lang):
            """Extract language-specific string from object or return as-is if string"""
            if isinstance(value, dict) and lang in value:
                return value[lang]
            elif isinstance(value, dict):
                return next(iter(value.values()), "")
            return value

        # Build enhanced experiences
        enhanced_experiences = []
        for i, bullet_result in enumerate(bullet_results, 1):
            project_name = bullet_result["project_name"]
            project_data = projects_database[project_name]

            # Format bullets as array of strings
            bullets_array = [b["text"] for b in bullet_result["bullets"]]

            enhanced_exp = {
                "role": bullet_result["role"],
                "company": project_data.get("company", user_info.get("name", "Freelance")),
                "location": extract_lang(project_data.get("location", {}), language) or "Remote",
                "start_date": project_data.get("start_date", "2023-01"),
                "end_date": project_data.get("end_date", "2024-12"),
                "bullets": bullets_array,
                "context": project_data.get("contexte", "")
            }
            enhanced_experiences.append(enhanced_exp)

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
            "experience": enhanced_experiences,
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
        print(f"  Step 3 (Enhancement):       {step3_time:6.2f}s")
        print(f"  Step 4 (Cover Letter):      {step4_time:6.2f}s")
        print(f"  Step 5 (JSON Build):        {step5_time:6.2f}s")
        print(f"  {'-' * 40}")
        print(f"  TOTAL:                      {total_time:6.2f}s")

        # Calculate average ATS score
        all_ats_scores = [br["average_ats_score"] for br in bullet_results]
        avg_ats_score = sum(all_ats_scores) / len(all_ats_scores) if all_ats_scores else 0

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
                    "enhancement": round(step3_time, 2),
                    "cover_letter": round(step4_time, 2),
                    "json_build": round(step5_time, 2)
                },
                "language": language,
                "projects_selected": [p["project_name"] for p in selected_projects],
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

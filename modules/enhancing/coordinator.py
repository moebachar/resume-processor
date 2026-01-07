"""
Experience Enhancement Coordinator (Async Version)

This module orchestrates the entire enhancement process by:
1. Selecting the best 3 projects from the database
2. Strategically distributing skills across experiences
3. Assigning optimal roles for each project
4. Determining enhancement intensity per project
5. Mapping relevant job responsibilities to each project
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from openai import AsyncOpenAI

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.config_loader import get_config


def build_coordinator_schema() -> dict:
    """
    Build JSON schema for coordinator output.

    Returns:
        dict: JSON schema for OpenAI Structured Outputs
    """
    return {
        "type": "object",
        "properties": {
            "selected_projects": {
                "type": "array",
                "description": "Exactly 3 selected projects with enhancement strategy",
                "items": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Exact name of the project from the database"
                        },
                        "selection_reasoning": {
                            "type": "string",
                            "description": "Brief explanation why this project was selected (50-100 words)"
                        },
                        "keywords_to_use": {
                            "type": "array",
                            "description": "List of 6-10 keywords/skills from the job that should be used in this project's bullets. These should be skills that naturally fit this project and are well-distributed across all 3 experiences.",
                            "items": {"type": "string"},
                            "minItems": 6,
                            "maxItems": 10
                        },
                        "target_role": {
                            "type": "string",
                            "description": "The job title for this experience. Should be different from other experiences and ATS-optimized for the target job. Can be from project's available roles or a smart hybrid."
                        },
                        "enhancement_level": {
                            "type": "string",
                            "enum": ["conservative", "moderate", "aggressive"],
                            "description": "How aggressively to adapt this project: conservative (70% authentic, perfect match), moderate (50/50, good match), aggressive (30% authentic, distant match)"
                        },
                        "responsibilities_to_incorporate": {
                            "type": "array",
                            "description": "2-3 specific job responsibilities that fit well with this project and should be reflected in the bullets",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 3
                        }
                    },
                    "required": [
                        "project_name",
                        "selection_reasoning",
                        "keywords_to_use",
                        "target_role",
                        "enhancement_level",
                        "responsibilities_to_incorporate"
                    ],
                    "additionalProperties": False
                },
                "minItems": 3,
                "maxItems": 3
            },
            "overall_strategy": {
                "type": "object",
                "properties": {
                    "skill_distribution_rationale": {
                        "type": "string",
                        "description": "Explanation of how skills are distributed across the 3 experiences"
                    },
                    "role_diversity_rationale": {
                        "type": "string",
                        "description": "Explanation of role selection strategy to show diversity and progression"
                    },
                    "estimated_ats_coverage": {
                        "type": "number",
                        "description": "Estimated percentage of job's must-have skills covered by the 3 projects",
                        "minimum": 0,
                        "maximum": 100
                    }
                },
                "required": [
                    "skill_distribution_rationale",
                    "role_diversity_rationale",
                    "estimated_ats_coverage"
                ],
                "additionalProperties": False
            }
        },
        "required": ["selected_projects", "overall_strategy"],
        "additionalProperties": False
    }


def create_coordinator_system_prompt() -> str:
    """
    Create system prompt for the coordinator.

    Returns:
        str: System prompt
    """
    return """You are an expert resume strategist and ATS optimization specialist.

MISSION: Select and strategize enhancement for 3 experiences that will create the strongest resume for the target job.

YOUR RESPONSIBILITIES:
1. ANALYZE the job requirements deeply (must-have skills, preferred skills, responsibilities)
2. EVALUATE all available projects for relevance and potential
3. SELECT exactly 3 projects that together provide:
   - Maximum coverage of job's must-have skills
   - Diverse skill sets (avoid repetition across experiences)
   - Authentic fit (projects that genuinely relate to the job)
   - Progressive story (shows growth and diverse capabilities)
4. FOR EACH PROJECT, strategize:
   a) Which specific keywords/skills to emphasize (6-10 per project)
   b) The optimal role title (different across experiences)
   c) How aggressively to adapt (conservative/moderate/aggressive)
   d) Which job responsibilities to incorporate (2-3 per project)

CRITICAL RULES FOR PROJECT SELECTION:
1. Prioritize projects that genuinely align with the job domain
2. Ensure the 3 projects together cover 70%+ of must-have skills
3. Select projects with different focuses to show versatility
4. Consider manual priority scores but don't rely solely on them
5. Balance technical depth with breadth

CRITICAL RULES FOR SKILL DISTRIBUTION:
1. Distribute skills strategically across all 3 experiences
2. Each project should have 6-10 unique skills (minimal overlap)
3. Prioritize must-have skills first, then preferred
4. Within each project, select skills that naturally work together
   - GOOD: Python + Scikit-learn + Docker (ML pipeline)
   - BAD: OpenCV + PowerBI + Kafka (unrelated technologies)
5. Avoid mentioning the same skill in multiple projects unless it's a core must-have
6. Ensure total coverage across 3 projects reaches 70%+ of must-have skills

CRITICAL RULES FOR ROLE SELECTION:
1. Each of the 3 experiences MUST have a DIFFERENT role title
2. Roles should show progression or diverse capabilities
3. Roles must be ATS-relevant to the target job
4. Use project's authentic roles when possible, create smart hybrids when needed
5. Examples of good role diversity:
   - Experience 1: "AI Engineer"
   - Experience 2: "Data Science Consultant"
   - Experience 3: "Machine Learning Engineer"

CRITICAL RULES FOR ENHANCEMENT LEVEL:
- Conservative (70% authentic): Project is a perfect/near-perfect match for the job
- Moderate (50/50): Project is a good match but needs some adaptation
- Aggressive (30% authentic): Project is relevant but from different domain/context

CRITICAL RULES FOR RESPONSIBILITIES:
- Select 2-3 job responsibilities that naturally fit each project
- These will be incorporated into bullets to show direct experience
- Choose responsibilities that the project genuinely addressed
- Distribute different responsibilities across the 3 projects

OUTPUT: JSON with selected_projects array and overall_strategy object.
"""


def create_coordinator_user_prompt(
    projects_database: Dict[str, Dict[str, Any]],
    job_data: Dict[str, Any]
) -> str:
    """
    Create user prompt for the coordinator.

    Args:
        projects_database: All available projects
        job_data: Structured job JSON

    Returns:
        str: User prompt
    """
    # Format projects database for the prompt
    projects_summary = ""
    for i, (project_name, project_data) in enumerate(projects_database.items(), 1):
        available_roles = project_data.get('metiers', [])
        roles_text = f"\n  Available Roles: {', '.join(available_roles)}" if available_roles else ""

        projects_summary += f"""
{i}. {project_name}
  Context: {project_data['contexte']}
  Domains: {', '.join(project_data.get('domains', []))}
  Technologies: {', '.join(project_data['technologies'][:10])}{'...' if len(project_data['technologies']) > 10 else ''}{roles_text}
  Priority Score: {project_data.get('priority', 0.5)}
  Achievements: {len(project_data.get('realisations', []))} listed
"""

    # Extract key job information
    must_have = job_data['technical_priorities']['must_have']
    preferred = job_data['technical_priorities']['preferred']
    all_tech_skills = job_data['technical_skills']
    responsibilities = job_data.get('responsibilities', [])

    prompt = f"""TARGET JOB:
Title: {job_data['job_title']}
Company: {job_data['company_name']}

MUST-HAVE SKILLS ({len(must_have)}):
{', '.join(must_have)}

PREFERRED SKILLS ({len(preferred)}):
{', '.join(preferred)}

ALL TECHNICAL SKILLS ({len(all_tech_skills)}):
{', '.join(all_tech_skills)}

KEY RESPONSIBILITIES ({len(responsibilities[:10])} shown):
{chr(10).join(f'  {i+1}. {resp}' for i, resp in enumerate(responsibilities[:10]))}

AVAILABLE PROJECTS ({len(projects_database)}):
{projects_summary}

YOUR TASK:
1. SELECT exactly 3 projects that together provide the best resume for this job
2. FOR EACH PROJECT, provide:
   a) keywords_to_use: 6-10 skills from the job that fit this project naturally and complement other experiences
   b) target_role: A unique role title (different from other 2 projects) that's ATS-optimized
   c) enhancement_level: conservative/moderate/aggressive based on project-job fit
   d) responsibilities_to_incorporate: 2-3 job responsibilities that this project can authentically address

STRATEGIC CONSIDERATIONS:
- Aim for 70%+ coverage of must-have skills across all 3 projects
- Distribute skills to minimize overlap between projects
- Within each project, group related/complementary skills
- Show role diversity across the 3 experiences
- Balance authenticity with ATS optimization
- Consider both technical fit and contextual relevance (consulting vs academic vs startup)

OUTPUT: JSON with your strategic plan for the 3 selected experiences.
"""

    return prompt


async def coordinate_enhancement(
    projects_database: Dict[str, Dict[str, Any]],
    job_data: Dict[str, Any],
    client: AsyncOpenAI,
    model: str = None
) -> Dict[str, Any]:
    """
    Coordinate the enhancement strategy for all experiences (async).

    Args:
        projects_database: Dictionary of all available projects
        job_data: Structured job JSON
        client: AsyncOpenAI client
        model: Model to use for coordination (default: gpt-4o-mini)

    Returns:
        Dict with enhancement strategy:
        {
            "selected_projects": [
                {
                    "project_name": str,
                    "selection_reasoning": str,
                    "keywords_to_use": List[str],
                    "target_role": str,
                    "enhancement_level": str,
                    "responsibilities_to_incorporate": List[str]
                }
            ],
            "overall_strategy": {
                "skill_distribution_rationale": str,
                "role_diversity_rationale": str,
                "estimated_ats_coverage": float
            }
        }
    """
    print("\n" + "=" * 70)
    print("ENHANCEMENT COORDINATOR (ASYNC)")
    print("=" * 70)

    # Load default model from config if not provided
    # Fallback chain: parameter → task-specific → module default → global default
    if model is None:
        model = (get_config('enhancing.coordinator.model') or
                 get_config('enhancing.default_model') or
                 get_config('openai.default_model', 'gpt-4o-mini'))

    # Build schema
    schema = build_coordinator_schema()

    # Create prompts
    system_prompt = create_coordinator_system_prompt()
    user_prompt = create_coordinator_user_prompt(projects_database, job_data)

    print(f"\nAnalyzing {len(projects_database)} projects for job: {job_data['job_title']}")
    print(f"Must-have skills: {len(job_data['technical_priorities']['must_have'])}")
    print(f"Total technical skills: {len(job_data['technical_skills'])}")
    print(f"\nCalling coordinator (model: {model})...")

    # Call OpenAI with Structured Outputs (async)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "enhancement_coordination",
                "strict": True,
                "schema": schema
            }
        },
        temperature=get_config('enhancing.coordinator.temperature', 0.7)
    )

    # Parse response
    result = json.loads(response.choices[0].message.content)

    # Print summary
    print("\n" + "=" * 70)
    print("[OK] COORDINATOR STRATEGY READY")
    print("=" * 70)

    print(f"\nSelected Projects:")
    for i, project in enumerate(result['selected_projects'], 1):
        print(f"\n{i}. {project['project_name']}")
        print(f"   Role: {project['target_role']}")
        print(f"   Enhancement: {project['enhancement_level']}")
        print(f"   Keywords ({len(project['keywords_to_use'])}): {', '.join(project['keywords_to_use'][:5])}...")
        print(f"   Responsibilities: {len(project['responsibilities_to_incorporate'])}")

    strategy = result['overall_strategy']
    print(f"\nOverall Strategy:")
    print(f"  Estimated ATS Coverage: {strategy['estimated_ats_coverage']}%")
    print(f"  Skill Distribution: {strategy['skill_distribution_rationale'][:100]}...")
    print(f"  Role Diversity: {strategy['role_diversity_rationale'][:100]}...")

    return result

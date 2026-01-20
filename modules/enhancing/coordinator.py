"""
Experience Enhancement Coordinator (Async Version)

This module orchestrates the entire enhancement process by:
1. Processing experience configurations with candidate projects
2. Selecting the best project from candidates for each experience
3. Applying role strategy (direct or enhanced) per experience
4. Applying content strategy (direct or enhanced) per experience
5. Ensuring no project is reused across experiences
6. Strategically distributing skills and responsibilities
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


# =============================================================================
# NEW DYNAMIC EXPERIENCE COORDINATION SYSTEM
# =============================================================================

def build_experiences_coordinator_schema(num_experiences: int) -> dict:
    """
    Build JSON schema for the new experiences coordinator output.

    Args:
        num_experiences: Number of experiences to configure

    Returns:
        dict: JSON schema for OpenAI Structured Outputs
    """
    return {
        "type": "object",
        "properties": {
            "selected_experiences": {
                "type": "array",
                "description": f"Exactly {num_experiences} experiences with selection and strategy",
                "items": {
                    "type": "object",
                    "properties": {
                        "experience_index": {
                            "type": "integer",
                            "description": "Index of the experience (0-based, matches input order)"
                        },
                        "selected_project": {
                            "type": "string",
                            "description": "Name of the selected project from candidates"
                        },
                        "selection_reasoning": {
                            "type": "string",
                            "description": "Brief explanation why this project was selected (30-50 words)"
                        },
                        "role_title": {
                            "type": "string",
                            "description": "The role title for this experience"
                        },
                        "role_source": {
                            "type": "string",
                            "enum": ["direct", "enhanced"],
                            "description": "Whether role was taken directly from project or enhanced for ATS"
                        },
                        "content_strategy": {
                            "type": "string",
                            "enum": ["direct", "enhanced"],
                            "description": "Strategy for bullet content (from config)"
                        },
                        "keywords_to_use": {
                            "type": "array",
                            "description": "Keywords to use if content_strategy is enhanced (6-10 items)",
                            "items": {"type": "string"}
                        },
                        "enhancement_level": {
                            "type": "string",
                            "enum": ["conservative", "moderate", "aggressive"],
                            "description": "Enhancement intensity if content_strategy is enhanced"
                        },
                        "responsibilities_to_incorporate": {
                            "type": "array",
                            "description": "Job responsibilities to incorporate if enhanced (2-3 items)",
                            "items": {"type": "string"}
                        }
                    },
                    "required": [
                        "experience_index",
                        "selected_project",
                        "selection_reasoning",
                        "role_title",
                        "role_source",
                        "content_strategy",
                        "keywords_to_use",
                        "enhancement_level",
                        "responsibilities_to_incorporate"
                    ],
                    "additionalProperties": False
                },
                "minItems": num_experiences,
                "maxItems": num_experiences
            },
            "overall_strategy": {
                "type": "object",
                "properties": {
                    "skill_distribution_rationale": {
                        "type": "string",
                        "description": "Explanation of how skills are distributed across experiences"
                    },
                    "role_diversity_rationale": {
                        "type": "string",
                        "description": "Explanation of role selection strategy"
                    },
                    "estimated_ats_coverage": {
                        "type": "number",
                        "description": "Estimated percentage of job's must-have skills covered",
                        "minimum": 0,
                        "maximum": 100
                    },
                    "direct_vs_enhanced_rationale": {
                        "type": "string",
                        "description": "Explanation of the mix of direct vs enhanced experiences"
                    }
                },
                "required": [
                    "skill_distribution_rationale",
                    "role_diversity_rationale",
                    "estimated_ats_coverage",
                    "direct_vs_enhanced_rationale"
                ],
                "additionalProperties": False
            }
        },
        "required": ["selected_experiences", "overall_strategy"],
        "additionalProperties": False
    }


def create_experiences_coordinator_system_prompt() -> str:
    """
    Create system prompt for the new experiences coordinator.

    Returns:
        str: System prompt
    """
    return """You are an expert resume strategist and ATS optimization specialist.

MISSION: For each experience configuration, select the best project from candidates and apply the specified strategies.

YOUR RESPONSIBILITIES:
1. FOR EACH EXPERIENCE in the configuration:
   a) EVALUATE the candidate projects for that experience
   b) SELECT the best project (considering job fit and uniqueness)
   c) APPLY the role strategy:
      - "direct": Choose the best role from project's available roles (metiers) - use exactly as-is
      - "enhanced": Choose a role and adapt it for ATS optimization
   d) APPLY the content strategy:
      - "direct": Content will be used as-is (still plan keywords for tracking)
      - "enhanced": Plan keywords, responsibilities, enhancement level

2. ENSURE GLOBAL CONSTRAINTS:
   - NO PROJECT can be used in more than one experience
   - Roles should show diversity and logical progression
   - Skills should be distributed strategically across enhanced experiences

CRITICAL RULES FOR PROJECT SELECTION:
1. Each project can ONLY be selected ONCE across all experiences
2. If a project appears in multiple candidate pools, prioritize where it fits best
3. Consider job alignment when selecting from multiple candidates
4. If only one candidate, that project must be used (if not already taken)

CRITICAL RULES FOR ROLE STRATEGY:
- "direct": Return EXACTLY one of the project's available roles (metiers) unchanged
- "enhanced": Adapt the role for better ATS matching while staying authentic

CRITICAL RULES FOR CONTENT STRATEGY:
- "direct": Set keywords_to_use to relevant skills (for tracking), but content won't be modified
- "enhanced": Plan full enhancement with keywords, responsibilities, and enhancement level

CRITICAL RULES FOR ENHANCED EXPERIENCES:
1. Distribute job keywords strategically (6-10 per enhanced experience)
2. Assign 2-3 relevant job responsibilities per enhanced experience
3. Set enhancement_level based on project-job fit:
   - conservative (70% authentic): Perfect match
   - moderate (50/50): Good match
   - aggressive (30% authentic): Distant match

OUTPUT: JSON with selected_experiences array and overall_strategy object.
"""


def create_experiences_coordinator_user_prompt(
    experiences_config: List[Dict[str, Any]],
    projects_database: Dict[str, Dict[str, Any]],
    job_data: Dict[str, Any]
) -> str:
    """
    Create user prompt for the experiences coordinator.

    Args:
        experiences_config: List of experience configurations
        projects_database: All available projects
        job_data: Structured job JSON

    Returns:
        str: User prompt
    """
    # Format experiences config
    experiences_text = ""
    for i, exp_config in enumerate(experiences_config):
        candidates = exp_config.get("candidate_projects", [])
        role_strategy = exp_config.get("role_strategy", "enhanced")
        content_strategy = exp_config.get("content_strategy", "enhanced")

        experiences_text += f"""
EXPERIENCE {i}:
  Candidate Projects: {', '.join(candidates)}
  Role Strategy: {role_strategy}
  Content Strategy: {content_strategy}
"""

    # Format projects details (only those that are candidates)
    all_candidates = set()
    for exp_config in experiences_config:
        all_candidates.update(exp_config.get("candidate_projects", []))

    projects_summary = ""
    for project_name in all_candidates:
        if project_name in projects_database:
            project_data = projects_database[project_name]
            available_roles = project_data.get('metiers', [])
            roles_text = f"\n    Available Roles: {', '.join(available_roles)}" if available_roles else ""

            projects_summary += f"""
  {project_name}:
    Context: {project_data.get('contexte', 'N/A')}
    Domains: {', '.join(project_data.get('domains', []))}
    Technologies: {', '.join(project_data.get('technologies', [])[:10])}{'...' if len(project_data.get('technologies', [])) > 10 else ''}{roles_text}
    Achievements: {len(project_data.get('realisations', []))} listed
"""

    # Extract key job information
    must_have = job_data.get('technical_priorities', {}).get('must_have', [])
    preferred = job_data.get('technical_priorities', {}).get('preferred', [])
    all_tech_skills = job_data.get('technical_skills', [])
    responsibilities = job_data.get('responsibilities', [])

    prompt = f"""TARGET JOB:
Title: {job_data.get('job_title', 'N/A')}
Company: {job_data.get('company_name', 'N/A')}

MUST-HAVE SKILLS ({len(must_have)}):
{', '.join(must_have)}

PREFERRED SKILLS ({len(preferred)}):
{', '.join(preferred)}

ALL TECHNICAL SKILLS ({len(all_tech_skills)}):
{', '.join(all_tech_skills)}

KEY RESPONSIBILITIES ({len(responsibilities[:10])} shown):
{chr(10).join(f'  {i+1}. {resp}' for i, resp in enumerate(responsibilities[:10]))}

=== EXPERIENCE CONFIGURATIONS ({len(experiences_config)} experiences) ===
{experiences_text}

=== CANDIDATE PROJECTS DETAILS ===
{projects_summary}

YOUR TASK:
For each experience configuration:
1. SELECT the best project from its candidate pool (ensuring no project reuse)
2. APPLY role_strategy: "direct" = use project's role as-is, "enhanced" = adapt for ATS
3. APPLY content_strategy: "direct" = content used as-is, "enhanced" = plan full enhancement
4. ENSURE no project appears in multiple experiences

STRATEGIC CONSIDERATIONS:
- Maximize ATS coverage across enhanced experiences
- Distribute skills to minimize overlap
- Show role diversity and progression
- Balance authenticity with optimization
- For "direct" content: still track which skills are present for metadata

OUTPUT: JSON with your strategic plan for all {len(experiences_config)} experiences.
"""

    return prompt


async def coordinate_experiences(
    experiences_config: List[Dict[str, Any]],
    projects_database: Dict[str, Dict[str, Any]],
    job_data: Dict[str, Any],
    client: AsyncOpenAI,
    model: str = None
) -> Dict[str, Any]:
    """
    Coordinate experience selection and strategy for each configured experience.

    This is the NEW coordinator that handles dynamic experience configurations
    with per-experience project candidates and strategies.

    Args:
        experiences_config: List of experience configurations, each containing:
            - candidate_projects: List of project names to choose from
            - role_strategy: "direct" | "enhanced"
            - content_strategy: "direct" | "enhanced"
        projects_database: Dictionary of all available projects
        job_data: Structured job JSON
        client: AsyncOpenAI client
        model: Model to use for coordination (default: gpt-4o-mini)

    Returns:
        Dict with experience strategies:
        {
            "selected_experiences": [
                {
                    "experience_index": int,
                    "selected_project": str,
                    "selection_reasoning": str,
                    "role_title": str,
                    "role_source": "direct" | "enhanced",
                    "content_strategy": "direct" | "enhanced",
                    "keywords_to_use": List[str],
                    "enhancement_level": str,
                    "responsibilities_to_incorporate": List[str]
                }
            ],
            "overall_strategy": {
                "skill_distribution_rationale": str,
                "role_diversity_rationale": str,
                "estimated_ats_coverage": float,
                "direct_vs_enhanced_rationale": str
            }
        }
    """
    print("\n" + "=" * 70)
    print("EXPERIENCE COORDINATOR (ASYNC) - DYNAMIC CONFIGURATION")
    print("=" * 70)

    # Load default model from config if not provided
    if model is None:
        model = (get_config('enhancing.coordinator.model') or
                 get_config('enhancing.default_model') or
                 get_config('openai.default_model', 'gpt-4o-mini'))

    num_experiences = len(experiences_config)

    # Validate experiences config
    all_candidates = set()
    for i, exp_config in enumerate(experiences_config):
        candidates = exp_config.get("candidate_projects", [])
        if not candidates:
            raise ValueError(f"Experience {i} has no candidate projects")
        for candidate in candidates:
            if candidate not in projects_database:
                raise ValueError(f"Project '{candidate}' not found in projects_database")
        all_candidates.update(candidates)

    print(f"\nConfigured experiences: {num_experiences}")
    print(f"Total unique candidate projects: {len(all_candidates)}")

    # Count strategies
    direct_content = sum(1 for e in experiences_config if e.get("content_strategy") == "direct")
    enhanced_content = num_experiences - direct_content
    print(f"Content strategies: {direct_content} direct, {enhanced_content} enhanced")

    # Build schema
    schema = build_experiences_coordinator_schema(num_experiences)

    # Create prompts
    system_prompt = create_experiences_coordinator_system_prompt()
    user_prompt = create_experiences_coordinator_user_prompt(
        experiences_config, projects_database, job_data
    )

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
                "name": "experiences_coordination",
                "strict": True,
                "schema": schema
            }
        },
        temperature=get_config('enhancing.coordinator.temperature', 0.7)
    )

    # Parse response
    result = json.loads(response.choices[0].message.content)

    # Validate no project reuse
    used_projects = set()
    for exp in result['selected_experiences']:
        project = exp['selected_project']
        if project in used_projects:
            raise ValueError(f"Coordinator error: Project '{project}' used in multiple experiences")
        used_projects.add(project)

    # Print summary
    print("\n" + "=" * 70)
    print("[OK] EXPERIENCE COORDINATION COMPLETE")
    print("=" * 70)

    print(f"\nSelected Experiences:")
    for exp in result['selected_experiences']:
        strategy_icon = "+" if exp['content_strategy'] == 'enhanced' else "="
        role_icon = "+" if exp['role_source'] == 'enhanced' else "="
        print(f"\n{exp['experience_index']}. {exp['selected_project']}")
        print(f"   Role [{role_icon}]: {exp['role_title']}")
        print(f"   Content [{strategy_icon}]: {exp['content_strategy']}")
        if exp['content_strategy'] == 'enhanced':
            print(f"   Enhancement: {exp['enhancement_level']}")
            print(f"   Keywords ({len(exp['keywords_to_use'])}): {', '.join(exp['keywords_to_use'][:5])}...")

    strategy = result['overall_strategy']
    print(f"\nOverall Strategy:")
    print(f"  Estimated ATS Coverage: {strategy['estimated_ats_coverage']}%")
    print(f"  Direct vs Enhanced: {strategy['direct_vs_enhanced_rationale'][:80]}...")

    return result

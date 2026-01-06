"""
Bullet Point Coordinator Module (Async Version)

Generates optimized bullet points based on coordinator's strategic plan.
This module works in tandem with coordinator.py to execute the enhancement strategy.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any
from openai import AsyncOpenAI

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.config_loader import get_config


def build_bullet_schema(num_bullets: int) -> dict:
    """
    Build JSON schema for bullet generation output.

    Args:
        num_bullets: Number of bullets to generate

    Returns:
        dict: JSON schema for OpenAI Structured Outputs
    """
    return {
        "type": "object",
        "properties": {
            "bullets": {
                "type": "array",
                "description": f"Exactly {num_bullets} optimized bullet points",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The bullet point text"
                        },
                        "ats_score": {
                            "type": "number",
                            "description": "ATS optimization score from 0 to 1",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "keywords_used": {
                            "type": "array",
                            "description": "Keywords from the PRIORITY KEYWORDS list that are LITERALLY present in this bullet text",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["text", "ats_score", "keywords_used"],
                    "additionalProperties": False
                },
                "minItems": num_bullets,
                "maxItems": num_bullets
            }
        },
        "required": ["bullets"],
        "additionalProperties": False
    }


def create_bullet_system_prompt(
    num_bullets: int,
    language: str,
    enhancement_level: str,
    max_bullet_length: int = 150
) -> str:
    """
    Create system prompt for bullet generation.

    Args:
        num_bullets: Number of bullets to generate
        language: Language code (fr or en)
        enhancement_level: conservative/moderate/aggressive
        max_bullet_length: Maximum characters per bullet (default: 150)

    Returns:
        str: System prompt
    """
    lang_config = {
        "fr": {
            "format": "[VERBE D'ACTION] + [TECHNOLOGIES] + [RESULTAT/IMPACT]",
            "examples": [
                "Developpe un pipeline ML avec Python et PyTorch pour automatiser la detection d'anomalies",
                "Deploye une architecture RAG utilisant LangChain et ChromaDB pour recherche semantique temps reel",
                "Optimise les performances systeme avec Docker et Kubernetes reduisant les couts de 40%"
            ]
        },
        "en": {
            "format": "[ACTION VERB] + [TECHNOLOGIES] + [OUTCOME/IMPACT]",
            "examples": [
                "Developed ML pipeline with Python and PyTorch to automate anomaly detection",
                "Deployed RAG architecture using LangChain and ChromaDB for real-time semantic search",
                "Optimized system performance with Docker and Kubernetes reducing costs by 40%"
            ]
        }
    }

    lang = lang_config.get(language, lang_config["en"])

    # Enhancement level instructions
    enhancement_instructions = {
        "conservative": """
ENHANCEMENT LEVEL: CONSERVATIVE (70% Authentic)
- Stay very close to the original project achievements
- Use job keywords naturally where they genuinely fit
- Prioritize authenticity over keyword stuffing
- Only adapt phrasing, not core content""",
        "moderate": """
ENHANCEMENT LEVEL: MODERATE (50/50 Balance)
- Balance original achievements with job requirements
- Adapt content to emphasize relevant aspects
- Use job keywords actively but naturally
- Reshape achievements to align with job responsibilities""",
        "aggressive": """
ENHANCEMENT LEVEL: AGGRESSIVE (30% Authentic)
- Transform achievements to strongly align with job
- Emphasize transferable aspects over literal project content
- Use job keywords extensively
- Focus on outcomes that match job requirements"""
    }

    return f"""You are an expert resume writer specializing in ATS optimization.

MISSION: Generate {num_bullets} bullet points for this experience following the coordinator's strategic plan.

{enhancement_instructions.get(enhancement_level, enhancement_instructions['moderate'])}

CRITICAL RULES:
1. Generate ALL {num_bullets} bullets AT ONCE
2. Use ONLY keywords from the PRIORITY KEYWORDS list provided
3. Each bullet follows format: {lang['format']}
4. MAXIMUM LENGTH: Each bullet must be {max_bullet_length} characters or less
5. TELL A COHERENT STORY: Bullets should show project progression (requirements => implementation => deployment)
6. DIVERSIFY ACTION VERBS: Use DIFFERENT action verbs for each bullet
7. INCORPORATE RESPONSIBILITIES: Reflect the TARGET RESPONSIBILITIES naturally in 2-3 bullets
8. BALANCE KEYWORDS: Distribute the priority keywords across bullets (don't repeat same keyword in multiple bullets)

BULLET FORMAT EXAMPLES (max {max_bullet_length} chars each):
{chr(10).join(f'  - {ex}' for ex in lang['examples'])}

KEYWORDS USAGE RULES:
1. ONLY list keywords that are LITERALLY present in your bullet text (word-for-word, case-insensitive)
2. ONLY list keywords from the PRIORITY KEYWORDS list
3. DO NOT list semantic matches (Azure != Cloud, RAG != AI)
4. Standard abbreviations allowed if commonly used (API, IA, ML, etc.)

ATS SCORING CRITERIA (per bullet):
- Keyword presence (35%): Contains 2-3 priority keywords LITERALLY
- Must-have coverage (25%): Uses must-have skills from job
- Responsibility alignment (20%): Reflects target responsibilities
- Professional format (15%): Clear structure and impact
- Readability (5%): Natural flow, not keyword-stuffed

Score each bullet from 0 to 1 based on these criteria.

OUTPUT: JSON with bullets array (text, ats_score, keywords_used).
"""


def create_bullet_user_prompt(
    project_name: str,
    project_data: Dict[str, Any],
    job_data: Dict[str, Any],
    coordinator_instructions: Dict[str, Any],
    num_bullets: int
) -> str:
    """
    Create user prompt for bullet generation.

    Args:
        project_name: Name of the project
        project_data: Project data from database
        job_data: Structured job JSON
        coordinator_instructions: Instructions from coordinator for this project
        num_bullets: Number of bullets to generate

    Returns:
        str: User prompt
    """
    # Extract coordinator instructions
    keywords_to_use = coordinator_instructions['keywords_to_use']
    target_role = coordinator_instructions['target_role']
    enhancement_level = coordinator_instructions['enhancement_level']
    responsibilities = coordinator_instructions['responsibilities_to_incorporate']
    reasoning = coordinator_instructions.get('selection_reasoning', '')

    # Extract must-have skills for reference
    must_have = job_data['technical_priorities']['must_have']

    prompt = f"""TARGET JOB:
Title: {job_data['job_title']}
Company: {job_data['company_name']}

YOUR PROJECT:
Name: {project_name}
Context: {project_data['contexte']}
Technologies: {', '.join(project_data['technologies'])}

Original Achievements:
{chr(10).join(f'  {i+1}. {achievement}' for i, achievement in enumerate(project_data['realisations']))}

COORDINATOR'S STRATEGIC PLAN FOR THIS PROJECT:
Selection Reasoning: {reasoning}

Target Role: {target_role}
Enhancement Level: {enhancement_level}

PRIORITY KEYWORDS TO USE ({len(keywords_to_use)}):
{', '.join(keywords_to_use)}

TARGET RESPONSIBILITIES TO INCORPORATE:
{chr(10).join(f'  {i+1}. {resp}' for i, resp in enumerate(responsibilities))}

MUST-HAVE SKILLS (for reference):
{', '.join(must_have)}

INSTRUCTIONS:
1. Generate {num_bullets} bullets that tell the story of this project's progression
2. Use the PRIORITY KEYWORDS strategically (aim to use all {len(keywords_to_use)} across the {num_bullets} bullets)
3. Distribute keywords evenly (2-3 keywords per bullet, no repetition)
4. Reflect 2-3 of the TARGET RESPONSIBILITIES naturally in your bullets
5. Use DIFFERENT action verbs for each bullet
6. Follow the {enhancement_level} enhancement approach
7. Calculate ATS score for each bullet (0-1)

CRITICAL - For keywords_used field:
- Review your generated bullet text
- Identify keywords that are LITERALLY in the text (exact match, case-insensitive)
- Check if each keyword is in the PRIORITY KEYWORDS list above
- ONLY include keywords that pass BOTH checks
- Example: If bullet says "Docker and Kubernetes", only claim ["Docker", "Kubernetes"] if both are in priority list

OUTPUT: JSON with bullets array.
"""

    return prompt


async def generate_bullets_with_coordinator(
    project_name: str,
    project_data: Dict[str, Any],
    job_data: Dict[str, Any],
    coordinator_instructions: Dict[str, Any],
    client: AsyncOpenAI,
    num_bullets: int = 4,
    max_bullet_length: int = 150,
    model: str = None,
    temperature: float = None
) -> Dict[str, Any]:
    """
    Generate bullets for one experience using coordinator's instructions (ASYNC).

    Args:
        project_name: Name of the project
        project_data: Project data from database
        job_data: Structured job JSON
        coordinator_instructions: Instructions from coordinator for this project
        client: AsyncOpenAI client
        num_bullets: Number of bullets to generate (default: 4)
        max_bullet_length: Maximum characters per bullet (default: 150)
        model: Model to use (default: gpt-4o-mini)
        temperature: Temperature for generation (default: 0.6)

    Returns:
        Dict with bullets and metadata:
        {
            "project_name": str,
            "role": str,
            "bullets": List[{"text": str, "ats_score": float, "keywords_used": List[str]}],
            "average_ats_score": float,
            "skills_covered": List[str],
            "enhancement_level": str,
            "coordinator_keywords": List[str]
        }
    """
    language = job_data["metadata"]["language"]
    enhancement_level = coordinator_instructions['enhancement_level']

    # Load defaults from config if not provided
    # Fallback chain: parameter → task-specific → module default → global default
    if model is None:
        model = (get_config('enhancing.bullet_coordinator.model') or
                 get_config('enhancing.default_model') or
                 get_config('openai.default_model', 'gpt-4o-mini'))
    if temperature is None:
        temperature = get_config('enhancing.bullet_coordinator.temperature') or get_config('enhancing.bullet_adaptation.temperature', 0.6)

    # Build schema
    schema = build_bullet_schema(num_bullets)

    # Create prompts
    system_prompt = create_bullet_system_prompt(num_bullets, language, enhancement_level, max_bullet_length)
    user_prompt = create_bullet_user_prompt(
        project_name,
        project_data,
        job_data,
        coordinator_instructions,
        num_bullets
    )

    # Call OpenAI with Structured Outputs (ASYNC)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "bullet_generation",
                "strict": True,
                "schema": schema
            }
        },
        temperature=temperature
    )

    # Parse response
    result = json.loads(response.choices[0].message.content)
    bullets_data = result["bullets"]

    # Calculate average ATS score
    avg_ats_score = sum(b["ats_score"] for b in bullets_data) / len(bullets_data)

    # Collect all skills used
    all_keywords = []
    for bullet in bullets_data:
        all_keywords.extend(bullet["keywords_used"])

    skills_covered = list(set(all_keywords))

    return {
        "project_name": project_name,
        "role": coordinator_instructions['target_role'],
        "bullets": bullets_data,
        "average_ats_score": round(avg_ats_score, 2),
        "skills_covered": skills_covered,
        "enhancement_level": enhancement_level,
        "coordinator_keywords": coordinator_instructions['keywords_to_use']
    }

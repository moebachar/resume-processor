"""
Job Description Structuring Module (Async Version)

Uses OpenAI's Structured Outputs feature to extract structured information
from raw job description text for resume adaptation.

This is the async version for use in the microservice.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from openai import AsyncOpenAI
from .job_schema import get_empty_job, validate_job

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.config_loader import get_config


def detect_language(text: str) -> str:
    """
    Detect the language of the job description text.

    Args:
        text: Job description text

    Returns:
        str: Language code ("fr" for French, "en" for English, etc.)
    """
    # Load language indicators from config
    french_indicators = get_config(
        'structuring.language_detection.french_indicators',
        ["le", "la", "les", "de", "du", "des", "et", "est", "vous", "notre"]
    )
    english_indicators = get_config(
        'structuring.language_detection.english_indicators',
        ["the", "and", "of", "to", "in", "for", "with", "on", "at", "by"]
    )

    text_lower = text.lower()
    words = text_lower.split()

    french_count = sum(1 for word in french_indicators if word in words)
    english_count = sum(1 for word in english_indicators if word in words)

    if french_count > english_count:
        return "fr"
    elif english_count > french_count:
        return "en"
    else:
        # Default to French since we're targeting French jobs
        return "fr"


def get_openai_client(api_key: str = None) -> AsyncOpenAI:
    """
    Initialize AsyncOpenAI client.

    Args:
        api_key: OpenAI API key. If None, will try to get from environment variable.

    Returns:
        AsyncOpenAI: Configured AsyncOpenAI client

    Raises:
        ValueError: If API key is not provided or found in environment
    """
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OpenAI API key not found. Please provide it as an argument or "
            "set the OPENAI_API_KEY environment variable."
        )

    return AsyncOpenAI(api_key=api_key)


def build_json_schema() -> dict:
    """
    Build the JSON schema for OpenAI's Structured Outputs.
    Must comply with strict mode requirements:
    - All objects must have "additionalProperties": False
    - All keys must be in "required" (no optional fields)

    Returns:
        dict: JSON schema for job extraction
    """
    return {
        "type": "object",
        "properties": {
            "job_title": {
                "type": "string",
                "description": "The title of the position"
            },
            "company_name": {
                "type": "string",
                "description": "Name of the company"
            },
            "location": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City where the job is located"
                    },
                    "remote_policy": {
                        "type": "string",
                        "enum": ["remote", "hybrid", "on-site", "not_specified"],
                        "description": "Remote work policy"
                    }
                },
                "required": ["city", "remote_policy"],
                "additionalProperties": False
            },
            "technical_skills": {
                "type": "array",
                "description": "All technical skills, tools, frameworks, technologies mentioned",
                "items": {
                    "type": "string"
                }
            },
            "soft_skills": {
                "type": "array",
                "description": "Soft skills and personal qualities required",
                "items": {
                    "type": "string"
                }
            },
            "experience_required": {
                "type": "object",
                "properties": {
                    "years": {
                        "type": "string",
                        "description": "Years of experience required (e.g., '1-3 ans', '5+ ans', 'Debutant accepte')"
                    },
                    "relevant_domains": {
                        "type": "array",
                        "description": "Relevant experience domains or fields",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["years", "relevant_domains"],
                "additionalProperties": False
            },
            "education_required": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "description": "Education level required (e.g., 'Bac+5', 'Master', 'ecole d'Ingenieur')"
                    },
                    "fields": {
                        "type": "array",
                        "description": "Relevant fields of study",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["level", "fields"],
                "additionalProperties": False
            },
            "languages": {
                "type": "array",
                "description": "Language requirements",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Language name (e.g., 'Franeais', 'Anglais')"
                        },
                        "level": {
                            "type": "string",
                            "description": "Required proficiency level (e.g., 'Courant', 'Professionnel', 'Bilingue')"
                        }
                    },
                    "required": ["name", "level"],
                    "additionalProperties": False
                }
            },
            "responsibilities": {
                "type": "array",
                "description": "Main responsibilities and missions of the role",
                "items": {
                    "type": "string"
                }
            },
            "keywords": {
                "type": "array",
                "description": "Important keywords from the job description for ATS optimization",
                "items": {
                    "type": "string"
                }
            },
            "company_values": {
                "type": "array",
                "description": "Company values mentioned in the job description",
                "items": {
                    "type": "string"
                }
            },
            "action_verbs": {
                "type": "array",
                "description": "Action verbs extracted from responsibilities (e.g., Développer, Concevoir, Implémenter)",
                "items": {
                    "type": "string"
                }
            },
            "technical_priorities": {
                "type": "object",
                "description": "Categorized technical skills by priority",
                "properties": {
                    "must_have": {
                        "type": "array",
                        "description": "Technologies mentioned multiple times or explicitly required",
                        "items": {
                            "type": "string"
                        }
                    },
                    "preferred": {
                        "type": "array",
                        "description": "Technologies mentioned once or as nice-to-have",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["must_have", "preferred"],
                "additionalProperties": False
            },
            "domain_terminology": {
                "type": "array",
                "description": "Domain-specific terms and jargon used in the job description",
                "items": {
                    "type": "string"
                }
            }
        },
        "required": [
            "job_title",
            "company_name",
            "location",
            "technical_skills",
            "soft_skills",
            "experience_required",
            "education_required",
            "languages",
            "responsibilities",
            "keywords",
            "company_values",
            "action_verbs",
            "technical_priorities",
            "domain_terminology"
        ],
        "additionalProperties": False
    }


def create_extraction_prompt() -> str:
    """
    Create the system prompt for job information extraction.

    Returns:
        str: System prompt for the LLM
    """
    return """You are an expert at extracting structured information from job descriptions.

Your task is to extract key information from job postings to help tailor resumes for CDI (permanent contract) positions.

Guidelines:
- Extract ALL technical skills mentioned (programming languages, frameworks, tools, platforms, technologies)
- Categorize technical skills into must_have (mentioned 2+ times or explicitly required) vs preferred (mentioned once)
- Extract action verbs from responsibilities (e.g., Développer, Concevoir, Implémenter, Accompagner)
- Identify domain-specific terminology and jargon
- Identify soft skills and personal qualities the company values
- List main responsibilities and missions clearly
- Extract important keywords that would help with ATS (Applicant Tracking System) optimization
- Identify company values when mentioned
- For experience, be specific about years and domains
- For education, extract the level and relevant fields
- For languages, include the required proficiency level
- For location, if remote work is mentioned, categorize as "remote", "hybrid", or "on-site"

IMPORTANT - Handling missing information:
- If information is NOT found in the job description, leave the field EMPTY
- For string fields: use an empty string ""
- For array fields: use an empty array []
- NEVER use placeholder text like "non spécifié", "not specified", "N/A", etc.
- Only extract information that is explicitly present in the text

Extract the information accurately and comprehensively."""


async def structure_job_description(
    job_text: str,
    source_url: str = "",
    api_key: str = None,
    model: str = None
) -> dict:
    """
    Extract structured information from a raw job description text using OpenAI (async).

    Args:
        job_text: Raw text of the job description
        source_url: URL of the original job posting (optional)
        api_key: OpenAI API key (optional, will use env var if not provided)
        model: OpenAI model to use (default: from config)

    Returns:
        dict: Structured job information following the schema, with success status
    """
    # Load default model from config if not provided
    # Fallback chain: parameter → task-specific → global default
    if model is None:
        model = get_config('structuring.model') or get_config('openai.default_model', 'gpt-4o-mini')

    try:
        # Initialize AsyncOpenAI client
        client = get_openai_client(api_key)

        # Build the JSON schema
        schema = build_json_schema()

        # Load temperature from config
        temperature = get_config('structuring.temperature', 0)

        # Create the API request with Structured Outputs (async)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": create_extraction_prompt()
                },
                {
                    "role": "user",
                    "content": f"Extract structured information from this job description:\n\n{job_text}"
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "job_extraction",
                    "strict": True,
                    "schema": schema
                }
            },
            temperature=temperature
        )

        # Parse the response
        extracted_data = json.loads(response.choices[0].message.content)

        # Detect language from the job text
        language = detect_language(job_text)

        # Add metadata
        extracted_data["metadata"] = {
            "source_url": source_url,
            "extraction_date": datetime.now().isoformat(),
            "language": language
        }

        # Validate the extracted data
        is_valid, errors = validate_job(extracted_data)

        if not is_valid:
            return {
                "success": False,
                "error": f"Validation failed: {errors}",
                "data": None
            }

        return {
            "success": True,
            "data": extracted_data,
            "error": None,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error during extraction: {str(e)}",
            "data": None
        }


def save_structured_job(job_data: dict, output_path: str) -> bool:
    """
    Save structured job data to a JSON file.

    Args:
        job_data: Structured job data dictionary
        output_path: Path where to save the JSON file

    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)

        print(f"✓ Structured job data saved to: {output_file}")
        return True

    except Exception as e:
        print(f"✗ Error saving file: {str(e)}")
        return False
